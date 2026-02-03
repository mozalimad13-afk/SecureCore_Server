"""
Reports Blueprint
Generates PDF reports with alerts, blocklist, and whitelist data
"""
from flask import Blueprint, request, jsonify, send_file, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.security import user_required
from datetime import datetime, timedelta
from io import BytesIO
from werkzeug.utils import secure_filename
import os
import logging

from app.models.user import User
from app.models.alert import Alert
from app.models.blocklist import BlockedIP
from app.models.whitelist import WhitelistedIP
from app.extensions import db
from config import Config

logger = logging.getLogger(__name__)

reports_bp = Blueprint('reports', __name__)


def _get_tenant_reports_dir(tenant_id: int) -> str:
    base_dir = str(getattr(Config, 'UPLOAD_FOLDER', None) or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads'))
    tenant_dir = os.path.join(base_dir, 'tenants', str(tenant_id), 'reports')
    os.makedirs(tenant_dir, exist_ok=True)
    return tenant_dir


def generate_pdf_report(user, alerts, blocked_ips, whitelisted_ips, start_date, end_date):
    """
    Generate PDF report with comprehensive security data
    
    Args:
        user: User object
        alerts: List of Alert objects
        blocked_ips: List of BlockedIP objects
        whitelisted_ips: List of WhitelistedIP objects
        start_date: Report start date
        end_date: Report end date
    
    Returns:
        BytesIO: PDF file buffer
    """
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, Image
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        
        # Create PDF buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch)
        
        # Container for elements
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        )
        
        # Title
        elements.append(Paragraph("SecureCore IDS Security Report", title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Report metadata
        metadata = [
            ['Report Generated:', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')],
            ['User:', user.name],
            ['Email:', user.email],
            ['Report Period:', f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"],
        ]
        
        metadata_table = Table(metadata, colWidths=[2*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#374151')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(metadata_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Executive Summary
        elements.append(Paragraph("Executive Summary", heading_style))
        
        # Calculate statistics
        total_alerts = len(alerts)
        critical_alerts = len([a for a in alerts if a.severity.lower() == 'critical'])
        high_alerts = len([a for a in alerts if a.severity.lower() == 'high'])
        # Per-alert "blocked" state is not stored; use blocklist count as the metric.
        blocked_threats = len(blocked_ips)
        
        summary_data = [
            ['Metric', 'Value'],
            ['Total Alerts', str(total_alerts)],
            ['Critical Severity', str(critical_alerts)],
            ['High Severity', str(high_alerts)],
            ['Blocked Threats', str(blocked_threats)],
            ['Active Blocked IPs', str(len(blocked_ips))],
            ['Whitelisted IPs', str(len(whitelisted_ips))],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Alerts Section
        if alerts:
            elements.append(Paragraph(f"Security Alerts ({total_alerts} total)", heading_style))
            
            alert_data = [['Date/Time', 'Type', 'Severity', 'Source IP', 'Status']]
            for alert in alerts[:50]:  # Limit to 50 most recent
                alert_data.append([
                    alert.created_at.strftime('%Y-%m-%d %H:%M') if alert.created_at else 'N/A',
                    alert.attack_type[:20],
                    alert.severity,
                    alert.source_ip,
                    'Logged'
                ])
            
            alert_table = Table(alert_data, colWidths=[1.3*inch, 1.5*inch, 0.8*inch, 1.2*inch, 0.8*inch])
            alert_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff1f1')]),
            ]))
            elements.append(alert_table)
            
            if len(alerts) > 50:
                elements.append(Spacer(1, 0.1*inch))
                elements.append(Paragraph(
                    f"<i>Note: Showing 50 most recent alerts out of {len(alerts)} total</i>",
                    styles['Normal']
                ))
        else:
            elements.append(Paragraph("No alerts recorded in this period.", styles['Normal']))
        
        elements.append(PageBreak())
        
        # Blocked IPs Section
        elements.append(Paragraph(f"Blocked IP Addresses ({len(blocked_ips)} total)", heading_style))
        
        if blocked_ips:
            blocked_data = [['IP Address', 'Reason', 'Blocked On', 'Type']]
            for ip in blocked_ips[:30]:
                blocked_data.append([
                    ip.ip_address,
                    ip.reason[:40] if ip.reason else 'No reason',
                    ip.created_at.strftime('%Y-%m-%d') if ip.created_at else 'N/A',
                    ip.block_type or 'Manual'
                ])
            
            blocked_table = Table(blocked_data, colWidths=[1.5*inch, 2.5*inch, 1.2*inch, 1*inch])
            blocked_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ea580c')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff7ed')]),
            ]))
            elements.append(blocked_table)
        else:
            elements.append(Paragraph("No blocked IP addresses.", styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        # Whitelisted IPs Section
        elements.append(Paragraph(f"Whitelisted IP Addresses ({len(whitelisted_ips)} total)", heading_style))
        
        if whitelisted_ips:
            whitelist_data = [['IP Address', 'Description', 'Added On']]
            for ip in whitelisted_ips[:30]:
                whitelist_data.append([
                    ip.ip_address,
                    ip.description[:50] if ip.description else 'No description',
                    ip.created_at.strftime('%Y-%m-%d') if ip.created_at else 'N/A'
                ])
            
            whitelist_table = Table(whitelist_data, colWidths=[1.5*inch, 3*inch, 1.5*inch])
            whitelist_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
            ]))
            elements.append(whitelist_table)
        else:
            elements.append(Paragraph("No whitelisted IP addresses.", styles['Normal']))
        
        elements.append(Spacer(1, 0.5*inch))
        
        # Footer
        footer_text = f"<i>This report was automatically generated by SecureCore IDS on {datetime.utcnow().strftime('%Y-%m-%d at %H:%M:%S UTC')}</i>"
        elements.append(Paragraph(footer_text, styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        return buffer
        
    except Exception as e:
        logger.error(f"PDF generation error: {str(e)}")
        raise


@reports_bp.route('', methods=['POST'])
@user_required
def generate_report():
    """
    Generate PDF security report for specified date range
    
    Request Body:
        start_date: ISO date string (YYYY-MM-DD)
        end_date: ISO date string (YYYY-MM-DD)
        include_alerts: boolean (default: true)
        include_blocklist: boolean (default: true)
        include_whitelist: boolean (default: true)
    
    Returns:
        PDF file download
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not user.tenant_id:
            return jsonify({'error': 'Tenant not configured for user'}), 500
        
        # Get request parameters
        data = request.get_json() or {}
        
        # Parse dates
        try:
            start_date_str = data.get('start_date')
            end_date_str = data.get('end_date')
            
            if not start_date_str or not end_date_str:
                # Default to last 30 days
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=30)
            else:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                
                # Ensure end_date is end of day
                end_date = end_date.replace(hour=23, minute=59, second=59)
                
        except ValueError as e:
            return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
        
        # Options
        include_alerts = data.get('include_alerts', True)
        include_blocklist = data.get('include_blocklist', True)
        include_whitelist = data.get('include_whitelist', True)
        
        # Fetch data
        alerts = []
        if include_alerts:
            alerts = Alert.query.filter(
                Alert.tenant_id == user.tenant_id,
                Alert.created_at >= start_date,
                Alert.created_at <= end_date
            ).order_by(Alert.created_at.desc()).all()
        
        blocked_ips = []
        if include_blocklist:
            blocked_ips = BlockedIP.query.filter(
                BlockedIP.tenant_id == user.tenant_id,
                BlockedIP.created_at >= start_date,
                BlockedIP.created_at <= end_date,
                BlockedIP.is_active == True
            ).order_by(BlockedIP.created_at.desc()).all()
        
        whitelisted_ips = []
        if include_whitelist:
            whitelisted_ips = WhitelistedIP.query.filter(
                WhitelistedIP.tenant_id == user.tenant_id,
                WhitelistedIP.created_at >= start_date,
                WhitelistedIP.created_at <= end_date,
                WhitelistedIP.is_active == True
            ).order_by(WhitelistedIP.created_at.desc()).all()
        
        # Generate PDF
        pdf_buffer = generate_pdf_report(
            user, alerts, blocked_ips, whitelisted_ips,
            start_date, end_date
        )
        
        # Generate filename (tenant-scoped filesystem)
        filename = secure_filename(f"SecureCore_Report_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.pdf")
        
        logger.info(f"Report generated for user {user_id}: {filename}")
        
        # Persist a copy for later listing/downloading (tenant-scoped)
        reports_dir = _get_tenant_reports_dir(user.tenant_id)
        with open(os.path.join(reports_dir, filename), 'wb') as f:
            f.write(pdf_buffer.getvalue())

        pdf_buffer.seek(0)
        return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"Report generation error: {str(e)}")
        return jsonify({'error': 'Failed to generate report'}), 500


@reports_bp.route('/preview', methods=['POST'])
@user_required
def preview_report():
    """
    Preview report statistics without generating PDF
    
    Returns summary of what will be included in the report
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not user.tenant_id:
            return jsonify({'error': 'Tenant not configured for user'}), 500
        data = request.get_json() or {}
        
        # Parse dates (same logic as generate_report)
        try:
            start_date_str = data.get('start_date')
            end_date_str = data.get('end_date')
            
            if not start_date_str or not end_date_str:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=30)
            else:
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                end_date = end_date.replace(hour=23, minute=59, second=59)
        except ValueError as e:
            return jsonify({'error': f'Invalid date format: {str(e)}'}), 400
        
        # Count records
        alert_count = Alert.query.filter(
            Alert.tenant_id == user.tenant_id,
            Alert.created_at >= start_date,
            Alert.created_at <= end_date
        ).count()
        
        blocked_count = BlockedIP.query.filter(
            BlockedIP.tenant_id == user.tenant_id,
            BlockedIP.created_at >= start_date,
            BlockedIP.created_at <= end_date,
            BlockedIP.is_active == True
        ).count()
        
        whitelist_count = WhitelistedIP.query.filter(
            WhitelistedIP.tenant_id == user.tenant_id,
            WhitelistedIP.created_at >= start_date,
            WhitelistedIP.created_at <= end_date,
            WhitelistedIP.is_active == True
        ).count()
        
        return jsonify({
            'preview': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'alert_count': alert_count,
                'blocked_ip_count': blocked_count,
                'whitelisted_ip_count': whitelist_count,
                'total_records': alert_count + blocked_count + whitelist_count
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Report preview error: {str(e)}")
        return jsonify({'error': 'Failed to generate preview'}), 500


@reports_bp.route('/list', methods=['GET'])
@user_required
def list_reports():
    """
    List all generated PDF reports from uploads folder
    
    Returns:
        JSON list of available reports with metadata
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not user.tenant_id:
            return jsonify({'error': 'Tenant not configured for user'}), 500

        reports_dir = _get_tenant_reports_dir(user.tenant_id)
        reports = []

        if os.path.exists(reports_dir):
            for filename in os.listdir(reports_dir):
                if filename.endswith('.pdf'):
                    filepath = os.path.join(reports_dir, filename)
                    stat = os.stat(filepath)
                    
                    reports.append({
                        'id': filename,
                        'name': filename.replace('.pdf', '').replace('-', ' '),
                        'filename': filename,
                        'date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d'),
                        'size': f"{stat.st_size / 1024:.1f} KB" if stat.st_size < 1024*1024 else f"{stat.st_size / (1024*1024):.1f} MB",
                        'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        # Sort by creation date, newest first
        reports.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({'reports': reports}), 200
        
    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}")
        return jsonify({'error': 'Failed to list reports'}), 500


@reports_bp.route('/download/<filename>', methods=['GET'])
@user_required
def download_report(filename):
    """
    Download a specific report from uploads folder
    
    Args:
        filename: Name of the PDF file to download
    
    Returns:
        PDF file download
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not user.tenant_id:
            return jsonify({'error': 'Tenant not configured for user'}), 500

        reports_dir = _get_tenant_reports_dir(user.tenant_id)
        # Security: ensure filename is safe
        filename = secure_filename(filename)
        
        if not filename.endswith('.pdf'):
            return jsonify({'error': 'Invalid file type'}), 400
        
        filepath = os.path.join(reports_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Report not found'}), 404
        
        return send_from_directory(reports_dir, filename, as_attachment=True)
        
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        return jsonify({'error': 'Failed to download report'}), 500


@reports_bp.route('/upload', methods=['POST'])
@user_required
def upload_report():
    """
    Upload a generated report to server
    
    Expects multipart/form-data with 'file' field
    
    Returns:
        Success message with filename
    """
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not user.tenant_id:
            return jsonify({'error': 'Tenant not configured for user'}), 500

        reports_dir = _get_tenant_reports_dir(user.tenant_id)
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Save file
        filepath = os.path.join(reports_dir, filename)
        file.save(filepath)
        
        logger.info(f"Report uploaded: {filename}")
        
        return jsonify({
            'message': 'Report uploaded successfully',
            'filename': filename
        }), 201
        
    except Exception as e:
        logger.error(f"Error uploading report: {str(e)}")
        return jsonify({'error': 'Failed to upload report'}), 500
