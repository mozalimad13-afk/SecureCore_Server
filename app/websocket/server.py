"""
WebSocket Server for Real-Time ML Inference
Handles WebSocket connections from IDS clients
Performs authentication, rate limiting, and real-time attack detection
"""
from flask_socketio import emit, disconnect, join_room, leave_room
from flask import request
import logging
import json
from datetime import datetime
import ipaddress
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from queue import Queue, Full, Empty
import threading

from app.extensions import db
from app.ml.inference import get_inference_engine
from app.services.alert_service import AlertService
from app.services.notification_service import NotificationService
from app.services.firebase_service import get_firebase_service
from app.models.websocket_session import WebSocketSession
from app.models.token import APIToken
from app.models.user import User
from config import Config
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InferenceTask:
    sid: str
    data: dict


class WebSocketInferenceServer:
    """Manages WebSocket connections for real-time inference"""
    
    def __init__(self, socketio, flask_app=None):
        """
        Initialize WebSocket server
        
        Args:
            socketio: Flask-SocketIO instance
        """
        self.socketio = socketio
        self.flask_app = flask_app
        self.ml_engine = get_inference_engine()
        self.alert_service = AlertService()
        self.notification_service = NotificationService()
        self.firebase_service = get_firebase_service()
        
        # Active sessions: {session_id: user_data}
        self.active_sessions = {}

        # Track active sessions per user to enforce caps
        self._active_sessions_by_user = defaultdict(set)

        # Simple per-user inference rate limiter (tokens per minute)
        self._inference_timestamps = defaultdict(deque)

        # Per-IP connection attempt limiter (simple sliding window)
        self._connect_timestamps = defaultdict(deque)

        # Per-session invalid-payload strikes (disconnect after threshold)
        self._invalid_strikes = defaultdict(int)

        # Background inference worker pool
        self._inference_queue: Queue[InferenceTask] = Queue(maxsize=Config.WS_MESSAGE_QUEUE_SIZE)
        self._inference_workers = []
        self._inference_stop = threading.Event()
        self._start_inference_workers()
        
        logger.info("WebSocket inference server initialized")

    def authenticate_connection(self, auth_data):
        """
        Authenticate WebSocket connection using API token
        
        Args:
            auth_data: dict with 'api_token' key
        
        Returns:
            tuple: (success: bool, user_data: dict or error_message: str)
        """
        try:
            if not auth_data or 'api_token' not in auth_data:
                return False, 'Missing API token'
            
            token_string = auth_data['api_token']
            
            # Validate and find token
            token = APIToken.find_by_token(token_string)
            
            if not token:
                return False, 'Invalid API token'
            
            if not token.is_active:
                return False, 'API token is inactive'

            # Enforce token expiry if configured
            if token.expires_at and token.expires_at <= datetime.utcnow():
                return False, 'API token expired'
            
            # Check if company is active
            company = token.company
            if not company:
                return False, 'Company not found'

            # Pick an active user from the company for the session (required by WebSocketSession)
            user = User.query.filter_by(company_id=company.id, is_active=True).first()
            if not user:
                return False, 'No active user found for this company'
            
            # Check subscription limits
            subscription = company.subscription
            if not subscription or subscription.status not in ['active', 'trial']:
                return False, 'Active subscription required'
            
            # Create session data
            user_data = {
                'company_id': company.id,
                'user_id': user.id,
                'email': user.email,
                'token_id': token.id,
                'subscription_plan': subscription.plan_name,
                'rate_limit': subscription.max_requests_per_minute
            }
            
            logger.info(f"WebSocket authentication successful for company {company.id} (user {user.id})")

            # Update token usage on successful authentication (best-effort)
            try:
                token.update_usage()
            except Exception:
                # Avoid breaking websocket connect on analytics write failure
                db.session.rollback()

            return True, user_data
            
        except Exception as e:
            logger.error(f"WebSocket authentication error: {str(e)}")
            return False, f'Authentication error: {str(e)}'
    
    def create_session(self, session_id, user_data):
        """Create WebSocket session in database"""
        try:
            session = WebSocketSession(
                user_id=user_data['user_id'],
                session_id=session_id,
                api_token_id=user_data['token_id'],
                connection_ip=request.remote_addr,
                is_active=True
            )
            db.session.add(session)
            db.session.commit()
            
            # Store in memory
            self.active_sessions[session_id] = user_data
            self._active_sessions_by_user[user_data['user_id']].add(session_id)
            
            logger.info(f"WebSocket session created: {session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session: {str(e)}")
            db.session.rollback()
            return None
    
    def end_session(self, session_id):
        """End WebSocket session"""
        try:
            # Update database
            session = WebSocketSession.query.filter_by(
                session_id=session_id,
                is_active=True
            ).first()
            
            if session:
                session.is_active = False
                session.disconnected_at = datetime.utcnow()
                db.session.commit()
            
            # Remove from memory
            if session_id in self.active_sessions:
                user_id = self.active_sessions[session_id].get('user_id')
                del self.active_sessions[session_id]
                if user_id is not None:
                    self._active_sessions_by_user[user_id].discard(session_id)
                    if not self._active_sessions_by_user[user_id]:
                        del self._active_sessions_by_user[user_id]
            
            logger.info(f"WebSocket session ended: {session_id}")
            
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            db.session.rollback()

    def _start_inference_workers(self):
        try:
            worker_count = int(getattr(Config, 'WS_INFERENCE_WORKERS', 4))
        except Exception:
            worker_count = 4

        worker_count = max(1, min(worker_count, 32))

        for idx in range(worker_count):
            t = threading.Thread(target=self._inference_worker_loop, name=f"ws-infer-{idx}", daemon=True)
            t.start()
            self._inference_workers.append(t)

        logger.info(f"Started {len(self._inference_workers)} inference worker(s)")

    def _inference_worker_loop(self):
        # Workers must run inside a Flask app context for DB access.
        app = self.flask_app
        if app is None:
            logger.error('WebSocketInferenceServer missing flask_app; inference workers may fail')

        while not self._inference_stop.is_set():
            try:
                task = self._inference_queue.get(timeout=0.25)
            except Empty:
                continue
                logger.info(f"/ws/inference worker dequeued sid={task.sid}")


            try:
                if app is not None:
                    logger.info(
                        f"/ws/inference worker processed sid={task.sid} keys={list(result.keys()) if isinstance(result, dict) else type(result)}"
                    )
                    with app.app_context():
                        result = self.process_inference_request(task.sid, task.data)
                    logger.info(f"/ws/inference emitted inference_result sid={task.sid}")
                else:
                    result = self.process_inference_request(task.sid, task.data)
            except Exception as e:
                logger.exception("Inference worker exception")
                result = {'error': f'Inference failed: {str(e)}', 'code': 'INFERENCE_ERROR'}
            finally:
                try:
                    self._inference_queue.task_done()
                except Exception:
                    pass

            try:
                self.socketio.emit('inference_result', result, to=task.sid, namespace='/ws/inference')
            except Exception:
                logger.exception("Failed to emit inference_result")

    def enqueue_inference(self, session_id: str, data: dict):
        try:
            self._inference_queue.put_nowait(InferenceTask(sid=session_id, data=data))
            return True, None
        except Full:
            return False, {'error': 'Server busy', 'code': 'QUEUE_FULL'}
    
    def process_inference_request(self, session_id, data):
        """
        Process ML inference request
        
        Args:
            session_id: WebSocket session ID
            data: dict with 'features' key (70 numerical values)
        
        Returns:
            dict: Inference result or error
        """
        try:
            # Get user data
            user_data = self.active_sessions.get(session_id)
            if not user_data:
                return {'error': 'Invalid session'}

            # Per-user rate limiting (in addition to any subscription checks)
            if not self._allow_inference(user_data):
                return {
                    'error': 'Rate limit exceeded',
                    'code': 'RATE_LIMIT'
                }
            
            # Validate features
            if 'features' not in data:
                self._invalid_strikes[session_id] += 1
                return {'error': 'Missing features', 'code': 'MISSING_FEATURES'}
            
            features = data['features']
            
            if not isinstance(features, list) or len(features) != Config.ML_INPUT_FEATURES:
                self._invalid_strikes[session_id] += 1
                return {'error': f'Invalid features: expected list of {Config.ML_INPUT_FEATURES} numerical values', 'code': 'INVALID_FEATURES'}

            ok, err = self._validate_features(features)
            if not ok:
                self._invalid_strikes[session_id] += 1
                return {'error': err, 'code': 'INVALID_FEATURES'}

            # Validate/sanitize metadata (IP/ports/proto/timestamp) to prevent DB bloat
            meta_ok, meta_err, safe_meta = self._validate_metadata(data)
            if not meta_ok:
                self._invalid_strikes[session_id] += 1
                return {'error': meta_err, 'code': 'INVALID_METADATA'}

            # Disconnect abusive sessions after repeated invalid payloads
            if self._invalid_strikes.get(session_id, 0) >= 5:
                return {'error': 'Too many invalid requests', 'code': 'ABUSE'}
            
            # Perform ML inference
            result = self.ml_engine.predict(features)

            # Ensure required fields exist even in mock mode
            if 'severity' not in result:
                result['severity'] = self._derive_severity(result)

            # Best-effort token usage update (avoid hard failing inference)
            try:
                api_token_id = user_data.get('token_id')
                if api_token_id:
                    token = APIToken.query.get(api_token_id)
                    if token:
                        token.update_usage()
            except Exception:
                db.session.rollback()
            
            # Update session statistics
            self._update_session_stats(session_id)
            
            # If attack detected, create alert
            if result['is_attack']:
                # Persist the sanitized metadata
                merged = dict(safe_meta)
                merged['features'] = features
                alert = self._create_alert(user_data, features, result, merged)
                result['alert_id'] = alert.id if alert else None
                
                # Send notification if high severity
                if result.get('severity') in ['high', 'critical']:
                    self._send_attack_notification(user_data, result)
            
            logger.info(
                f"Inference completed for user {user_data['user_id']}: "
                f"{result['attack_type']} ({result['confidence']:.2%})"
            )
            
            return result
            
        except ValueError as e:
            logger.error(f"Inference validation error: {str(e)}")
            return {'error': str(e)}
        except Exception as e:
            logger.error(f"Inference processing error: {str(e)}")
            return {'error': f'Inference failed: {str(e)}'}
    
    def _update_session_stats(self, session_id):
        """Update session statistics"""
        try:
            session = WebSocketSession.query.filter_by(
                session_id=session_id,
                is_active=True
            ).first()
            
            if session:
                session.inference_count += 1
                session.last_activity_at = datetime.utcnow()
                db.session.commit()
                
        except Exception as e:
            logger.error(f"Failed to update session stats: {str(e)}")
            db.session.rollback()
    
    def _create_alert(self, user_data, features, result, metadata):
        """Create alert in database"""
        try:
            model_name = result.get('model_name')
            if not model_name:
                # In mock mode or on older clients, the model identifier may be missing.
                model_name = 'unknown'

            alert_data = {
                'company_id': user_data.get('company_id'),
                'user_id': user_data['user_id'],
                'source_ip': metadata.get('source_ip', 'unknown'),
                'source_port': metadata.get('source_port'),
                'destination_ip': metadata.get('destination_ip'),
                'destination_port': metadata.get('destination_port'),
                'protocol': metadata.get('protocol'),
                'attack_type': result['attack_type'],
                'severity': result['severity'],
                'confidence': result['confidence'],
                'raw_features': json.dumps(features),
                'model_name': model_name,
                'metadata': json.dumps(metadata)
            }
            
            alert = self.alert_service.create_alert(alert_data)
            
            logger.info(f"Alert created: {alert.id}")

            # Mobile push via Firebase (best-effort). This targets the same user
            # that receives realtime UI updates.
            try:
                self.firebase_service.send_notification(
                    user_id=user_data['user_id'],
                    title=f"{str(result.get('severity', 'unknown')).upper()} Security Alert",
                    body=f"{result.get('attack_type')} detected",
                    data={
                        'type': 'alert',
                        'alert_id': str(getattr(alert, 'id', '')),
                        'severity': str(result.get('severity', 'unknown')),
                        'attack_type': str(result.get('attack_type', 'unknown')),
                        'confidence': str(result.get('confidence', '')),
                    },
                )
            except Exception:
                logger.exception('Failed to send Firebase push for alert')

            # Realtime push (user-specific + tenant dashboards)
            try:
                company_id = user_data.get('company_id')
                user_id = user_data.get('user_id')
                payload = {
                    'id': alert.id,
                    'attack_type': result.get('attack_type'),
                    'severity': result.get('severity'),
                    'confidence': float(result.get('confidence') or 0.0),
                    'source_ip': metadata.get('source_ip', 'unknown'),
                    'source_port': metadata.get('source_port'),
                    'destination_ip': metadata.get('destination_ip'),
                    'destination_port': metadata.get('destination_port'),
                    'protocol': metadata.get('protocol'),
                    'created_at': datetime.utcnow().isoformat(),
                }
                if company_id is not None:
                    # Broadcast to company room for all dashboards
                    self.socketio.emit('alert_created', payload, room=f"company_{company_id}", namespace='/ws/ui')
            except Exception:
                logger.exception('Failed to emit alert_created')

            return alert
            
        except Exception as e:
            logger.exception("Failed to create alert")
            return None

    def _validate_features(self, features):
        """Strict validation for exactly 70 numeric features.

        - Must be int/float (bool not allowed)
        - No NaN/Inf
        - Bounded to keep payload sane and prevent model abuse
        """
        if not isinstance(features, list) or len(features) != Config.ML_INPUT_FEATURES:
            return False, f"Invalid features: expected list of {Config.ML_INPUT_FEATURES} numerical values"

        for idx, value in enumerate(features):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return False, f"Feature {idx} must be a number"
            # Reject NaN/Inf
            if value != value or value in (float('inf'), float('-inf')):
                return False, f"Feature {idx} must be finite"
            # Conservative numeric bounds; widen if your preprocessor expects larger magnitudes.
            if value < -1e9 or value > 1e9:
                return False, f"Feature {idx} out of range"

        return True, None

    def _allow_inference(self, user_data):
        """Sliding-window limiter per user (max per minute)."""
        user_id = user_data['user_id']
        max_per_minute = int(user_data.get('rate_limit') or 0)

        # Fallback to config if subscription missing/invalid (defense in depth)
        if max_per_minute <= 0:
            max_per_minute = 60

        now = time.time()
        window = 60.0
        q = self._inference_timestamps[user_id]

        while q and (now - q[0]) > window:
            q.popleft()

        if len(q) >= max_per_minute:
            return False

        q.append(now)
        return True

    def allow_connect(self, remote_ip: str) -> bool:
        """Simple per-IP connect attempt limiter (sliding window)."""
        if not remote_ip:
            return True

        now = time.time()
        window = 60.0
        max_attempts = 30  # per minute per IP
        q = self._connect_timestamps[remote_ip]

        while q and (now - q[0]) > window:
            q.popleft()

        if len(q) >= max_attempts:
            return False

        q.append(now)
        return True

    def _validate_metadata(self, data):
        """Validate and sanitize metadata fields used for alerts.

        Returns: (ok: bool, err: str|None, safe_meta: dict)
        """

        def _norm_ip(value):
            if value is None:
                return None
            if not isinstance(value, str):
                return None
            value = value.strip()
            if not value:
                return None
            try:
                return str(ipaddress.ip_address(value))
            except Exception:
                return None

        def _norm_port(value):
            if value is None:
                return None
            try:
                p = int(value)
            except Exception:
                return None
            if p < 0 or p > 65535:
                return None
            return p

        def _norm_proto(value):
            if value is None:
                return None
            if isinstance(value, (int, float)):
                value = str(int(value))
            if not isinstance(value, str):
                return None
            v = value.strip().upper()
            if v in {'TCP', 'UDP', 'ICMP'}:
                return v
            # Accept common numeric protocol IDs
            if v in {'6'}:
                return 'TCP'
            if v in {'17'}:
                return 'UDP'
            if v in {'1'}:
                return 'ICMP'
            return 'OTHER'

        def _norm_ts(value):
            if value is None:
                return datetime.utcnow().isoformat()
            if not isinstance(value, str):
                return datetime.utcnow().isoformat()
            value = value.strip()
            if not value:
                return datetime.utcnow().isoformat()
            # Do not parse deeply; keep bounded string length
            return value[:64]

        safe = {
            'source_ip': _norm_ip(data.get('source_ip')),
            'source_port': _norm_port(data.get('source_port')),
            'destination_ip': _norm_ip(data.get('destination_ip')),
            'destination_port': _norm_port(data.get('destination_port')),
            'protocol': _norm_proto(data.get('protocol')),
            'timestamp': _norm_ts(data.get('timestamp')),
        }

        # Require at least source_ip + destination_ip for alert storage.
        if safe['source_ip'] is None or safe['destination_ip'] is None:
            return False, 'Invalid or missing source/destination IP', {}

        # Ensure ports are present for TCP/UDP.
        if safe['protocol'] in {'TCP', 'UDP'}:
            if safe['source_port'] is None or safe['destination_port'] is None:
                return False, 'Invalid or missing ports for TCP/UDP', {}

        return True, None, safe
    
    def _send_attack_notification(self, user_data, result):
        """Send notification for detected attack"""
        try:
            company_id = user_data.get('company_id')
            if not company_id:
                return

            # Fetch all active users in the company
            company_users = User.query.filter_by(company_id=company_id, is_active=True).all()
            
            # Send Firebase notification to original user (already handled or kept for individual push)
            self.firebase_service.send_notification(
                user_id=user_data['user_id'],
                title=f"{str(result.get('severity', 'unknown')).upper()} Security Alert",
                body=f"{result['attack_type']} detected with {result['confidence']:.0%} confidence",
                data={
                    'type': 'security_alert',
                    'severity': str(result.get('severity', 'unknown')),
                    'attack_type': result['attack_type'],
                    'confidence': str(result['confidence'])
                }
            )
            
            notification = None
            # Create in-app notification for ALL company users
            for user in company_users:
                notif = self.notification_service.create_notification(
                    tenant_id=company_id,
                    user_id=user.id,
                    title=f"{str(result.get('severity', 'unknown')).upper()} Security Alert",
                    message=f"{result['attack_type']} detected",
                    type='alert'
                )
                if user.id == user_data['user_id']:
                    notification = notif

            # Realtime push to UI
            try:
                company_id = user_data.get('company_id')
                if notification is not None and company_id is not None:
                    # Broadcast to company room so all online members see the popup/update
                    payload = {
                        'id': getattr(notification, 'id', None),
                        'title': getattr(notification, 'title', None),
                        'message': getattr(notification, 'message', None),
                        'type': getattr(notification, 'type', 'alert'),
                        'created_at': getattr(notification, 'created_at', None).isoformat() if getattr(notification, 'created_at', None) else datetime.utcnow().isoformat(),
                        'is_read': False,
                    }
                    self.socketio.emit('notification_created', payload, room=f"company_{company_id}", namespace='/ws/ui')
            except Exception:
                logger.exception('Failed to emit notification_created')
            
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")

    def _derive_severity(self, result: dict) -> str:
        """Derive severity from confidence using configured thresholds.

        This keeps WS behavior stable when models are not loaded (mock results).
        """
        try:
            confidence = float(result.get('confidence') or 0.0)
        except Exception:
            confidence = 0.0

        thresholds = getattr(Config, 'ALERT_SEVERITY_THRESHOLDS', None) or {
            'critical': 0.95,
            'high': 0.85,
            'medium': 0.70,
            'low': 0.0,
        }

        # Choose the highest severity whose threshold is met
        ordered = [('critical', thresholds.get('critical', 0.95)),
                   ('high', thresholds.get('high', 0.85)),
                   ('medium', thresholds.get('medium', 0.70)),
                   ('low', thresholds.get('low', 0.0))]
        for name, cutoff in ordered:
            try:
                if confidence >= float(cutoff):
                    return name
            except Exception:
                continue
        return 'low'


# Global server instance
ws_server = None


def register_websocket_handlers(socketio, flask_app=None):
    """
    Register WebSocket event handlers
    
    Args:
        socketio: Flask-SocketIO instance
    """
    global ws_server
    from flask import current_app
    ws_server = WebSocketInferenceServer(socketio, flask_app=flask_app)
    
    @socketio.on('connect', namespace='/ws/inference')
    def handle_connect(auth):
        """Handle WebSocket connection"""
        try:
            # Simple per-IP connection attempt rate limiting
            remote_ip = request.remote_addr or ''
            if not ws_server.allow_connect(remote_ip):
                emit('error', {'message': 'Too many connection attempts', 'code': 'CONNECT_RATE_LIMIT'})
                disconnect()
                return False

            # Authenticate
            success, result = ws_server.authenticate_connection(auth)
            
            if not success:
                logger.warning(f"WebSocket authentication failed: {result}")
                emit('error', {'message': result})
                disconnect()
                return False
            
            # Create session
            session_id = request.sid

            # Enforce connection cap per user before persisting session
            existing = ws_server._active_sessions_by_user.get(result['user_id'])
            if existing and len(existing) >= Config.WS_MAX_CONNECTIONS_PER_USER:
                emit('error', {'message': 'Too many active connections', 'code': 'CONNECTION_LIMIT'})
                disconnect()
                return False

            session = ws_server.create_session(session_id, result)
            
            if not session:
                emit('error', {'message': 'Failed to create session'})
                disconnect()
                return False
            
            # Join company room only (inference is company-wide, not user-specific)
            # Using company_id (tenant_id) for single session per company
            join_room(f"company_{result['company_id']}")
            
            # Send connection success
            emit('connected', {
                'message': 'Connected successfully',
                'session_id': session_id,
                'rate_limit': result['rate_limit']
            })
            
            logger.info(f"WebSocket client connected: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            emit('error', {'message': 'Connection failed'})
            disconnect()
            return False
    
    @socketio.on('disconnect', namespace='/ws/inference')
    def handle_disconnect():
        """Handle WebSocket disconnection"""
        session_id = request.sid
        
        if session_id in ws_server.active_sessions:
            user_data = ws_server.active_sessions[session_id]
            # Leave company room (inference is company-wide)
            leave_room(f"company_{user_data.get('company_id')}")
        
        ws_server.end_session(session_id)
        logger.info(f"WebSocket client disconnected: {session_id}")
    
    @socketio.on('inference', namespace='/ws/inference')
    def handle_inference(data):
        """Handle inference request"""
        session_id = request.sid

        # Trace requests in smoke tests and diagnose timeouts.
        logger.info(f"/ws/inference received inference sid={session_id}")

        # Require an authenticated session
        if session_id not in ws_server.active_sessions:
            emit('error', {'message': 'Unauthorized', 'code': 'UNAUTHORIZED'})
            disconnect()
            return
        
        ok, err = ws_server.enqueue_inference(session_id, data)
        if not ok:
            logger.warning(f"/ws/inference enqueue failed sid={session_id} err={err}")
            emit('inference_result', err)
            return

        try:
            qsize = ws_server._inference_queue.qsize()
        except Exception:
            qsize = -1
        logger.info(f"/ws/inference enqueued sid={session_id} qsize={qsize}")

        # Optional ack to keep clients responsive
        emit('inference_queued', {'timestamp': datetime.utcnow().isoformat()})
    
    @socketio.on('ping', namespace='/ws/inference')
    def handle_ping():
        """Handle ping for keep-alive"""
        emit('pong', {'timestamp': datetime.utcnow().isoformat()})

    # -----------------------------
    # UI namespace (browser clients)
    # Auth: JWT cookie (no API tokens)
    # -----------------------------
    @socketio.on('connect', namespace='/ws/ui')
    def handle_ui_connect(auth=None):
        try:
            # Verify JWT from cookies/headers (configured for cookies)
            verify_jwt_in_request(optional=False)
            user_id = get_jwt_identity()
            if not user_id:
                emit('error', {'message': 'Unauthorized', 'code': 'UNAUTHORIZED'})
                disconnect()
                return False

            user = User.query.get(user_id)
            if not user or not user.is_active or not user.company_id:
                emit('error', {'message': 'Unauthorized', 'code': 'UNAUTHORIZED'})
                disconnect()
                return False

            # Join user-specific rooms for real-time notifications
            # Each user gets their own room for personalized notifications
            join_room(f"user_{user.id}")
            # Also join company room for company-wide broadcasts
            join_room(f"company_{user.company_id}")

            emit('connected', {
                'message': 'UI connected successfully',
                'user_id': user.id,
                'company_id': user.company_id,
            })
            return True
        except Exception:
            emit('error', {'message': 'Unauthorized', 'code': 'UNAUTHORIZED'})
            disconnect()
            return False

    @socketio.on('disconnect', namespace='/ws/ui')
    def handle_ui_disconnect():
        # Rooms are automatically left on disconnect.
        return
    
    logger.info("WebSocket handlers registered")
