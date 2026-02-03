CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE companies (
	id INTEGER NOT NULL, 
	public_id VARCHAR(32) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	company VARCHAR(255), 
	phone_number VARCHAR(32), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_companies_public_id ON companies (public_id);
CREATE TABLE users (
	id INTEGER NOT NULL, 
	company_id INTEGER, 
	email VARCHAR(255) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	is_active BOOLEAN, 
	created_at DATETIME, 
	last_login DATETIME, 
	country VARCHAR(100), 
	email_verified BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE
);
CREATE INDEX ix_users_is_active ON users (is_active);
CREATE INDEX ix_users_role ON users (role);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_company_id ON users (company_id);
CREATE TABLE user_company_roles (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	company_id INTEGER NOT NULL, 
	role VARCHAR(32) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_company_role UNIQUE (user_id, company_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE
);
CREATE INDEX ix_user_company_roles_company_id ON user_company_roles (company_id);
CREATE INDEX ix_user_company_roles_user_id ON user_company_roles (user_id);
CREATE INDEX ix_user_company_roles_role ON user_company_roles (role);
CREATE TABLE fcm_devices (
	id INTEGER NOT NULL, 
	company_id INTEGER, 
	user_id INTEGER NOT NULL, 
	device_id_hash VARCHAR(64), 
	device_id_encrypted BLOB, 
	device_token_encrypted BLOB, 
	device_name VARCHAR(255), 
	device_type VARCHAR(50), 
	device_platform VARCHAR(50), 
	app_version VARCHAR(50), 
	last_seen_at DATETIME, 
	is_active BOOLEAN, 
	last_notified_at DATETIME, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE INDEX ix_fcm_devices_company_id ON fcm_devices (company_id);
CREATE INDEX ix_fcm_devices_user_id ON fcm_devices (user_id);
CREATE INDEX ix_fcm_devices_is_active ON fcm_devices (is_active);
CREATE INDEX ix_fcm_devices_device_id_hash ON fcm_devices (device_id_hash);
CREATE TABLE csrf_tokens (
	id INTEGER NOT NULL, 
	token_hash VARCHAR(255) NOT NULL, 
	user_id INTEGER, 
	session_id VARCHAR(255), 
	is_used BOOLEAN, 
	created_at DATETIME, 
	expires_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);
CREATE UNIQUE INDEX ix_csrf_tokens_token_hash ON csrf_tokens (token_hash);
CREATE INDEX ix_csrf_tokens_is_used ON csrf_tokens (is_used);
CREATE INDEX ix_csrf_tokens_expires_at ON csrf_tokens (expires_at);
CREATE TABLE audit_logs (
	id INTEGER NOT NULL, 
	company_id INTEGER, 
	user_id INTEGER, 
	action VARCHAR(100) NOT NULL, 
	resource_type VARCHAR(100) NOT NULL, 
	resource_id INTEGER, 
	details JSON, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX ix_audit_logs_company_id ON audit_logs (company_id);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);
CREATE TABLE admin_broadcasts (
	id INTEGER NOT NULL, 
	company_id INTEGER, 
	sender_id INTEGER, 
	title VARCHAR(255) NOT NULL, 
	message TEXT NOT NULL, 
	target_type VARCHAR(50) NOT NULL, 
	recipient_count INTEGER, 
	sent_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE, 
	FOREIGN KEY(sender_id) REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX ix_admin_broadcasts_company_id ON admin_broadcasts (company_id);
CREATE TABLE user_countries (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	location_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_location UNIQUE (user_id, location_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(location_id) REFERENCES locations (id) ON DELETE CASCADE
);
CREATE INDEX ix_user_countries_location_id ON user_countries (location_id);
CREATE INDEX ix_user_countries_user_id ON user_countries (user_id);
CREATE TABLE notifications (
	id INTEGER NOT NULL, 
	company_id INTEGER, 
	user_id INTEGER, 
	title VARCHAR(255) NOT NULL, 
	message TEXT NOT NULL, 
	type VARCHAR(20) NOT NULL, 
	priority VARCHAR(20), 
	is_read BOOLEAN, 
	related_alert_id INTEGER, 
	related_type VARCHAR(50), 
	related_id INTEGER, 
	link VARCHAR(512), 
	created_at DATETIME, 
	read_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(related_alert_id) REFERENCES "alerts_old" (id)
);
CREATE INDEX ix_notifications_created_at ON notifications (created_at);
CREATE INDEX ix_notifications_user_id ON notifications (user_id);
CREATE INDEX ix_notifications_company_id ON notifications (company_id);
CREATE INDEX ix_notifications_is_read ON notifications (is_read);
CREATE TABLE websocket_sessions (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	session_id VARCHAR(255) NOT NULL, 
	api_token_id INTEGER NOT NULL, 
	connection_ip VARCHAR(45), 
	is_active BOOLEAN, 
	connected_at DATETIME, 
	disconnected_at DATETIME, 
	last_activity_at DATETIME, 
	inference_count INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(api_token_id) REFERENCES "api_tokens_old" (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX ix_websocket_sessions_session_id ON websocket_sessions (session_id);
CREATE INDEX ix_websocket_sessions_is_active ON websocket_sessions (is_active);
CREATE INDEX ix_websocket_sessions_user_id ON websocket_sessions (user_id);
CREATE TABLE companies_countries (
                  company_id INTEGER NOT NULL,
                  location_id INTEGER NOT NULL,
                  PRIMARY KEY (company_id, location_id),
                  CONSTRAINT fk_cc_company FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                  CONSTRAINT fk_cc_location FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
                );
CREATE TABLE IF NOT EXISTS "locations" (
                  id INTEGER PRIMARY KEY,
                  code VARCHAR(2) NOT NULL,
                  name VARCHAR(100) NOT NULL
                );
CREATE UNIQUE INDEX uq_location_code ON locations(code);
CREATE UNIQUE INDEX uq_location_name ON locations(name);
CREATE INDEX ix_locations_code ON locations(code);
CREATE TABLE roles (
	id INTEGER NOT NULL, 
	name VARCHAR(32) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
CREATE UNIQUE INDEX ix_roles_name ON roles (name);
CREATE TABLE users_roles (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	company_id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_company_role_id UNIQUE (user_id, company_id, role_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE, 
	FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE
);
CREATE INDEX ix_users_roles_company_id ON users_roles (company_id);
CREATE INDEX ix_users_roles_user_id ON users_roles (user_id);
CREATE INDEX ix_users_roles_role_id ON users_roles (role_id);
CREATE TABLE company_settings (
	id INTEGER NOT NULL, 
	company_id INTEGER NOT NULL, 
	email_notifications BOOLEAN, 
	sms_notifications BOOLEAN, 
	webhook_notifications BOOLEAN, 
	webhook_url VARCHAR(500), 
	daily_digest BOOLEAN, 
	weekly_report BOOLEAN, 
	digest_time VARCHAR(10), 
	backup_frequency VARCHAR(20), 
	last_backup DATETIME, 
	next_backup DATETIME, 
	alert_reminder_enabled BOOLEAN, 
	alert_reminder_interval INTEGER, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX ix_company_settings_company_id ON company_settings (company_id);
CREATE TABLE user_profiles (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	display_name VARCHAR(255), 
	profile_picture VARCHAR(500), 
	bio TEXT, 
	timezone VARCHAR(50), 
	language VARCHAR(10), 
	theme VARCHAR(20), 
	two_factor_enabled BOOLEAN, 
	two_factor_secret VARCHAR(255), 
	email_on_mention BOOLEAN, 
	email_on_alert BOOLEAN, 
	push_notifications BOOLEAN, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX ix_user_profiles_user_id ON user_profiles (user_id);
CREATE TABLE api_tokens (
                                id INTEGER PRIMARY KEY,
                                company_id INTEGER,
                                token_hash VARCHAR(255) UNIQUE NOT NULL,
                                token_prefix VARCHAR(20) NOT NULL,
                                name VARCHAR(100),
                                is_active BOOLEAN DEFAULT 1,
                                requests_today INTEGER DEFAULT 0,
                                last_used_at DATETIME,
                                created_at DATETIME,
                                expires_at DATETIME,
                                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                            );
CREATE INDEX ix_api_tokens_company_id ON api_tokens(company_id);
CREATE INDEX ix_api_tokens_token_hash ON api_tokens(token_hash);
CREATE INDEX ix_api_tokens_is_active ON api_tokens(is_active);
CREATE TABLE alerts (
                                id INTEGER PRIMARY KEY,
                                company_id INTEGER,
                                source_ip VARCHAR(45) NOT NULL,
                                source_port INTEGER,
                                destination_ip VARCHAR(45),
                                destination_port INTEGER,
                                protocol VARCHAR(10),
                                attack_type VARCHAR(100) NOT NULL,
                                severity VARCHAR(20) NOT NULL,
                                confidence FLOAT NOT NULL,
                                raw_features TEXT,
                                created_at DATETIME,
                                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
                            );
CREATE INDEX ix_alerts_company_id ON alerts(company_id);
CREATE INDEX ix_alerts_source_ip ON alerts(source_ip);
CREATE INDEX ix_alerts_attack_type ON alerts(attack_type);
CREATE INDEX ix_alerts_severity ON alerts(severity);
CREATE INDEX ix_alerts_created_at ON alerts(created_at);
CREATE TABLE blocked_ips (
                                id INTEGER PRIMARY KEY,
                                company_id INTEGER,
                                ip_address VARCHAR(45) NOT NULL,
                                reason VARCHAR(255),
                                related_alert_id INTEGER,
                                block_type VARCHAR(20) DEFAULT 'manual',
                                is_active BOOLEAN DEFAULT 1,
                                expires_at DATETIME,
                                ufw_rule_number INTEGER,
                                snort_rule_id VARCHAR(100),
                                created_at DATETIME,
                                deactivated_at DATETIME,
                                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                                FOREIGN KEY (related_alert_id) REFERENCES alerts(id)
                            );
CREATE INDEX ix_blocked_ips_company_id ON blocked_ips(company_id);
CREATE INDEX ix_blocked_ips_ip_address ON blocked_ips(ip_address);
CREATE INDEX ix_blocked_ips_is_active ON blocked_ips(is_active);
CREATE TABLE whitelisted_ips (
                                id INTEGER PRIMARY KEY,
                                company_id INTEGER,
                                ip_address VARCHAR(45) NOT NULL,
                                description VARCHAR(255),
                                is_active BOOLEAN DEFAULT 1,
                                created_at DATETIME,
                                created_by INTEGER,
                                expires_at DATETIME,
                                deactivated_at DATETIME,
                                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
                                FOREIGN KEY (created_by) REFERENCES users(id)
                            );
CREATE INDEX ix_whitelisted_ips_company_id ON whitelisted_ips(company_id);
CREATE INDEX ix_whitelisted_ips_ip_address ON whitelisted_ips(ip_address);
CREATE INDEX ix_whitelisted_ips_is_active ON whitelisted_ips(is_active);
CREATE TABLE IF NOT EXISTS "payment_methods" (
                            id INTEGER NOT NULL,
                            company_id INTEGER NOT NULL,
                            card_last4 VARCHAR(4) NOT NULL,
                            card_brand VARCHAR(20),
                            card_holder_name VARCHAR(100) NOT NULL,
                            expiry_month VARCHAR(2) NOT NULL,
                            expiry_year VARCHAR(2) NOT NULL,
                            billing_address VARCHAR(255),
                            city VARCHAR(100),
                            zip_code VARCHAR(20),
                            is_default BOOLEAN NOT NULL,
                            is_active BOOLEAN NOT NULL,
                            created_at DATETIME NOT NULL,
                            updated_at DATETIME NOT NULL,
                            PRIMARY KEY (id),
                            FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE CASCADE
                        );
CREATE INDEX ix_payment_methods_company_id ON payment_methods (company_id);
CREATE TABLE subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                plan_name VARCHAR(100) NOT NULL,
                plan_price NUMERIC(10, 2) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'trial',
                start_date DATE NOT NULL DEFAULT (DATE('now')),
                end_date DATE,
                next_billing_date DATE,
                max_requests_per_minute INTEGER DEFAULT 1000,
                max_requests_per_month INTEGER DEFAULT 1000000,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
            );
CREATE INDEX ix_subscriptions_company_id ON subscriptions (company_id);
CREATE INDEX ix_subscriptions_status ON subscriptions (status);
