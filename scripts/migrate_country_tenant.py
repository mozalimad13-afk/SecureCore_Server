#!/usr/bin/env python3
"""
Schema migration: add countries and tenant fields, and remove payment_methods.country
- Create locations table
- Create user_countries association
- Add users.country
- Add tenants.company, tenants.phone_number
- Remove payment_methods.country (SQLite table recreation)
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / 'data' / 'securecore.db'

COUNTRIES = [
    ('AF', 'Afghanistan'), ('AL', 'Albania'), ('DZ', 'Algeria'), ('AS', 'American Samoa'),
    ('AD', 'Andorra'), ('AO', 'Angola'), ('AI', 'Anguilla'), ('AQ', 'Antarctica'),
    ('AG', 'Antigua and Barbuda'), ('AR', 'Argentina'), ('AM', 'Armenia'), ('AW', 'Aruba'),
    ('AU', 'Australia'), ('AT', 'Austria'), ('AZ', 'Azerbaijan'), ('BS', 'Bahamas'),
    ('BH', 'Bahrain'), ('BD', 'Bangladesh'), ('BB', 'Barbados'), ('BY', 'Belarus'),
    ('BE', 'Belgium'), ('BZ', 'Belize'), ('BJ', 'Benin'), ('BM', 'Bermuda'),
    ('BT', 'Bhutan'), ('BO', 'Bolivia'), ('BQ', 'Bonaire, Sint Eustatius and Saba'),
    ('BA', 'Bosnia and Herzegovina'), ('BW', 'Botswana'), ('BV', 'Bouvet Island'),
    ('BR', 'Brazil'), ('IO', 'British Indian Ocean Territory'), ('BN', 'Brunei Darussalam'),
    ('BG', 'Bulgaria'), ('BF', 'Burkina Faso'), ('BI', 'Burundi'), ('KH', 'Cambodia'),
    ('CM', 'Cameroon'), ('CA', 'Canada'), ('CV', 'Cape Verde'), ('KY', 'Cayman Islands'),
    ('CF', 'Central African Republic'), ('TD', 'Chad'), ('CL', 'Chile'), ('CN', 'China'),
    ('CX', 'Christmas Island'), ('CC', 'Cocos (Keeling) Islands'), ('CO', 'Colombia'),
    ('KM', 'Comoros'), ('CG', 'Congo'), ('CD', 'Congo (Democratic Republic)'),
    ('CK', 'Cook Islands'), ('CR', 'Costa Rica'), ('CI', "Côte d'Ivoire"), ('HR', 'Croatia'),
    ('CU', 'Cuba'), ('CW', 'Curaçao'), ('CY', 'Cyprus'), ('CZ', 'Czechia'),
    ('DK', 'Denmark'), ('DJ', 'Djibouti'), ('DM', 'Dominica'), ('DO', 'Dominican Republic'),
    ('EC', 'Ecuador'), ('EG', 'Egypt'), ('SV', 'El Salvador'), ('GQ', 'Equatorial Guinea'),
    ('ER', 'Eritrea'), ('EE', 'Estonia'), ('SZ', 'Eswatini'), ('ET', 'Ethiopia'),
    ('FK', 'Falkland Islands'), ('FO', 'Faroe Islands'), ('FJ', 'Fiji'), ('FI', 'Finland'),
    ('FR', 'France'), ('GF', 'French Guiana'), ('PF', 'French Polynesia'), ('TF', 'French Southern Territories'),
    ('GA', 'Gabon'), ('GM', 'Gambia'), ('GE', 'Georgia'), ('DE', 'Germany'),
    ('GH', 'Ghana'), ('GI', 'Gibraltar'), ('GR', 'Greece'), ('GL', 'Greenland'),
    ('GD', 'Grenada'), ('GP', 'Guadeloupe'), ('GU', 'Guam'), ('GT', 'Guatemala'),
    ('GG', 'Guernsey'), ('GN', 'Guinea'), ('GW', 'Guinea-Bissau'), ('GY', 'Guyana'),
    ('HT', 'Haiti'), ('HM', 'Heard Island and McDonald Islands'), ('VA', 'Holy See'),
    ('HN', 'Honduras'), ('HK', 'Hong Kong'), ('HU', 'Hungary'), ('IS', 'Iceland'),
    ('IN', 'India'), ('ID', 'Indonesia'), ('IR', 'Iran'), ('IQ', 'Iraq'),
    ('IE', 'Ireland'), ('IM', 'Isle of Man'), ('IL', 'Israel'), ('IT', 'Italy'),
    ('JM', 'Jamaica'), ('JP', 'Japan'), ('JE', 'Jersey'), ('JO', 'Jordan'),
    ('KZ', 'Kazakhstan'), ('KE', 'Kenya'), ('KI', 'Kiribati'), ('KP', 'Korea (North)'),
    ('KR', 'Korea (South)'), ('KW', 'Kuwait'), ('KG', 'Kyrgyzstan'), ('LA', 'Lao PDR'),
    ('LV', 'Latvia'), ('LB', 'Lebanon'), ('LS', 'Lesotho'), ('LR', 'Liberia'),
    ('LY', 'Libya'), ('LI', 'Liechtenstein'), ('LT', 'Lithuania'), ('LU', 'Luxembourg'),
    ('MO', 'Macao'), ('MK', 'North Macedonia'), ('MG', 'Madagascar'), ('MW', 'Malawi'),
    ('MY', 'Malaysia'), ('MV', 'Maldives'), ('ML', 'Mali'), ('MT', 'Malta'),
    ('MH', 'Marshall Islands'), ('MQ', 'Martinique'), ('MR', 'Mauritania'), ('MU', 'Mauritius'),
    ('YT', 'Mayotte'), ('MX', 'Mexico'), ('FM', 'Micronesia'), ('MD', 'Moldova'),
    ('MC', 'Monaco'), ('MN', 'Mongolia'), ('ME', 'Montenegro'), ('MS', 'Montserrat'),
    ('MA', 'Morocco'), ('MZ', 'Mozambique'), ('MM', 'Myanmar'), ('NA', 'Namibia'),
    ('NR', 'Nauru'), ('NP', 'Nepal'), ('NL', 'Netherlands'), ('NC', 'New Caledonia'),
    ('NZ', 'New Zealand'), ('NI', 'Nicaragua'), ('NE', 'Niger'), ('NG', 'Nigeria'),
    ('NU', 'Niue'), ('NF', 'Norfolk Island'), ('MP', 'Northern Mariana Islands'),
    ('NO', 'Norway'), ('OM', 'Oman'), ('PK', 'Pakistan'), ('PW', 'Palau'),
    ('PS', 'Palestine, State of'), ('PA', 'Panama'), ('PG', 'Papua New Guinea'),
    ('PY', 'Paraguay'), ('PE', 'Peru'), ('PH', 'Philippines'), ('PN', 'Pitcairn'),
    ('PL', 'Poland'), ('PT', 'Portugal'), ('PR', 'Puerto Rico'), ('QA', 'Qatar'),
    ('RE', 'Réunion'), ('RO', 'Romania'), ('RU', 'Russian Federation'), ('RW', 'Rwanda'),
    ('BL', 'Saint Barthélemy'), ('SH', 'Saint Helena'), ('KN', 'Saint Kitts and Nevis'),
    ('LC', 'Saint Lucia'), ('MF', 'Saint Martin (French part)'), ('PM', 'Saint Pierre and Miquelon'),
    ('VC', 'Saint Vincent and the Grenadines'), ('WS', 'Samoa'), ('SM', 'San Marino'),
    ('ST', 'Sao Tome and Principe'), ('SA', 'Saudi Arabia'), ('SN', 'Senegal'),
    ('RS', 'Serbia'), ('SC', 'Seychelles'), ('SL', 'Sierra Leone'), ('SG', 'Singapore'),
    ('SX', 'Sint Maarten (Dutch part)'), ('SK', 'Slovakia'), ('SI', 'Slovenia'),
    ('SB', 'Solomon Islands'), ('SO', 'Somalia'), ('ZA', 'South Africa'), ('GS', 'South Georgia and the South Sandwich Islands'),
    ('SS', 'South Sudan'), ('ES', 'Spain'), ('LK', 'Sri Lanka'), ('SD', 'Sudan'),
    ('SR', 'Suriname'), ('SJ', 'Svalbard and Jan Mayen'), ('SE', 'Sweden'),
    ('CH', 'Switzerland'), ('SY', 'Syrian Arab Republic'), ('TW', 'Taiwan'),
    ('TJ', 'Tajikistan'), ('TZ', 'Tanzania'), ('TH', 'Thailand'), ('TL', 'Timor-Leste'),
    ('TG', 'Togo'), ('TK', 'Tokelau'), ('TO', 'Tonga'), ('TT', 'Trinidad and Tobago'),
    ('TN', 'Tunisia'), ('TR', 'Türkiye'), ('TM', 'Turkmenistan'), ('TC', 'Turks and Caicos Islands'),
    ('TV', 'Tuvalu'), ('UG', 'Uganda'), ('UA', 'Ukraine'), ('AE', 'United Arab Emirates'),
    ('GB', 'United Kingdom'), ('US', 'United States'), ('UM', 'United States Minor Outlying Islands'),
    ('UY', 'Uruguay'), ('UZ', 'Uzbekistan'), ('VU', 'Vanuatu'), ('VE', 'Venezuela'),
    ('VN', 'Viet Nam'), ('VG', 'Virgin Islands (British)'), ('VI', 'Virgin Islands (U.S.)'),
    ('WF', 'Wallis and Futuna'), ('EH', 'Western Sahara'), ('YE', 'Yemen'),
    ('ZM', 'Zambia'), ('ZW', 'Zimbabwe')
]

def table_exists(cur, name):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None

def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # locations
    if not table_exists(cur, 'locations'):
        cur.execute("""
        CREATE TABLE locations (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE
        )
        """)
        cur.executemany("INSERT INTO locations(code, name) VALUES(?, ?)", COUNTRIES)
        print('Created locations and seeded')
    else:
        for code, name in COUNTRIES:
            cur.execute("INSERT OR IGNORE INTO locations(code, name) VALUES(?, ?)", (code, name))
        print('Upserted locations')

    # user_countries
    if not table_exists(cur, 'user_countries'):
        cur.execute("""
        CREATE TABLE user_countries (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            location_id INTEGER NOT NULL,
            UNIQUE(user_id, location_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(location_id) REFERENCES locations(id) ON DELETE CASCADE
        )
        """)
        print('Created user_countries')

    # users.country
    if not column_exists(cur, 'users', 'country'):
        cur.execute("ALTER TABLE users ADD COLUMN country TEXT")
        print('Added users.country')

    # tenants.company (SKIP - using 'companies' table instead)
    # if not column_exists(cur, 'tenants', 'company'):
    #     cur.execute("ALTER TABLE tenants ADD COLUMN company TEXT")
    #     print('Added tenants.company')

    # tenants.phone_number (SKIP - using 'companies' table instead)
    # if not column_exists(cur, 'tenants', 'phone_number'):
    #     cur.execute("ALTER TABLE tenants ADD COLUMN phone_number TEXT")
    #     print('Added tenants.phone_number')

    # payment_methods.country removal via table recreate (SKIP - not needed currently)
    # if column_exists(cur, 'payment_methods', 'country'):
    #     # Create new table without country
    #     cur.execute("""
    #     CREATE TABLE IF NOT EXISTS payment_methods_new (
    #         id INTEGER PRIMARY KEY,
    #         tenant_id INTEGER,
    #         user_id INTEGER NOT NULL,
    #         card_last4 TEXT NOT NULL,
    #         card_brand TEXT,
    #         card_holder_name TEXT NOT NULL,
    #         expiry_month TEXT NOT NULL,
    #         expiry_year TEXT NOT NULL,
    #         billing_address TEXT,
    #         city TEXT,
    #         zip_code TEXT,
    #         is_default INTEGER NOT NULL DEFAULT 0,
    #         is_active INTEGER NOT NULL DEFAULT 1,
    #         created_at TEXT NOT NULL,
    #         updated_at TEXT NOT NULL,
    #         FOREIGN KEY(user_id) REFERENCES users(id)
    #     )
    #     """)
    #     # Copy data
    #     cur.execute("""
    #     INSERT INTO payment_methods_new(
    #         id, tenant_id, user_id, card_last4, card_brand, card_holder_name,
    #         expiry_month, expiry_year, billing_address, city, zip_code,
    #         is_default, is_active, created_at, updated_at
    #     )
    #     SELECT id, tenant_id, user_id, card_last4, card_brand, card_holder_name,
    #            expiry_month, expiry_year, billing_address, city, zip_code,
    #            is_default, is_active, created_at, updated_at
    #     FROM payment_methods
    #     """)
    #     # Replace table
    #     cur.execute("DROP TABLE payment_methods")
    #     cur.execute("ALTER TABLE payment_methods_new RENAME TO payment_methods")
    #     print('Removed payment_methods.country by table recreation')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    migrate()
    print('Migration complete')
