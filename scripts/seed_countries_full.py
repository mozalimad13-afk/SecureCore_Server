#!/usr/bin/env python3
"""Seed the `locations` table with ISO 3166-1 countries.

This script targets the current SQLAlchemy schema where `locations` is global
(no `company_id`). Per-company availability can be modeled via the
`companies_countries` join table.

Run from `server/`:
    PYTHONPATH=$PWD:$PYTHONPATH python scripts/seed_countries_full.py

Optional DB override:
    DATABASE_URL=sqlite:////abs/path/securecore.db PYTHONPATH=$PWD:$PYTHONPATH python scripts/seed_countries_full.py
"""

from __future__ import annotations

from app import create_app
from app.extensions import db
from app.models.location import Location

# ISO 3166-1 alpha-2 country list (code, name)
COUNTRIES = [
    ('AF', 'Afghanistan'), ('AX', 'Åland Islands'), ('AL', 'Albania'), ('DZ', 'Algeria'), ('AS', 'American Samoa'),
    ('AD', 'Andorra'), ('AO', 'Angola'), ('AI', 'Anguilla'), ('AQ', 'Antarctica'), ('AG', 'Antigua and Barbuda'),
    ('AR', 'Argentina'), ('AM', 'Armenia'), ('AW', 'Aruba'), ('AU', 'Australia'), ('AT', 'Austria'),
    ('AZ', 'Azerbaijan'), ('BS', 'Bahamas'), ('BH', 'Bahrain'), ('BD', 'Bangladesh'), ('BB', 'Barbados'),
    ('BY', 'Belarus'), ('BE', 'Belgium'), ('BZ', 'Belize'), ('BJ', 'Benin'), ('BM', 'Bermuda'),
    ('BT', 'Bhutan'), ('BO', 'Bolivia'), ('BQ', 'Caribbean Netherlands'), ('BA', 'Bosnia and Herzegovina'), ('BW', 'Botswana'),
    ('BV', 'Bouvet Island'), ('BR', 'Brazil'), ('IO', 'British Indian Ocean Territory'), ('BN', 'Brunei Darussalam'), ('BG', 'Bulgaria'),
    ('BF', 'Burkina Faso'), ('BI', 'Burundi'), ('KH', 'Cambodia'), ('CM', 'Cameroon'), ('CA', 'Canada'),
    ('CV', 'Cabo Verde'), ('KY', 'Cayman Islands'), ('CF', 'Central African Republic'), ('TD', 'Chad'), ('CL', 'Chile'),
    ('CN', 'China'), ('CX', 'Christmas Island'), ('CC', 'Cocos (Keeling) Islands'), ('CO', 'Colombia'), ('KM', 'Comoros'),
    ('CG', 'Congo'), ('CD', 'Congo, Democratic Republic'), ('CK', 'Cook Islands'), ('CR', 'Costa Rica'), ('CI', 'Côte d’Ivoire'),
    ('HR', 'Croatia'), ('CU', 'Cuba'), ('CW', 'Curaçao'), ('CY', 'Cyprus'), ('CZ', 'Czechia'),
    ('DK', 'Denmark'), ('DJ', 'Djibouti'), ('DM', 'Dominica'), ('DO', 'Dominican Republic'), ('EC', 'Ecuador'),
    ('EG', 'Egypt'), ('SV', 'El Salvador'), ('GQ', 'Equatorial Guinea'), ('ER', 'Eritrea'), ('EE', 'Estonia'),
    ('SZ', 'Eswatini'), ('ET', 'Ethiopia'), ('FK', 'Falkland Islands'), ('FO', 'Faroe Islands'), ('FJ', 'Fiji'),
    ('FI', 'Finland'), ('FR', 'France'), ('GF', 'French Guiana'), ('PF', 'French Polynesia'), ('TF', 'French Southern Territories'),
    ('GA', 'Gabon'), ('GM', 'Gambia'), ('GE', 'Georgia'), ('DE', 'Germany'), ('GH', 'Ghana'),
    ('GI', 'Gibraltar'), ('GR', 'Greece'), ('GL', 'Greenland'), ('GD', 'Grenada'), ('GP', 'Guadeloupe'),
    ('GU', 'Guam'), ('GT', 'Guatemala'), ('GG', 'Guernsey'), ('GN', 'Guinea'), ('GW', 'Guinea-Bissau'),
    ('GY', 'Guyana'), ('HT', 'Haiti'), ('HM', 'Heard Island and McDonald Islands'), ('VA', 'Holy See'), ('HN', 'Honduras'),
    ('HK', 'Hong Kong'), ('HU', 'Hungary'), ('IS', 'Iceland'), ('IN', 'India'), ('ID', 'Indonesia'),
    ('IR', 'Iran'), ('IQ', 'Iraq'), ('IE', 'Ireland'), ('IM', 'Isle of Man'), ('IL', 'Israel'),
    ('IT', 'Italy'), ('JM', 'Jamaica'), ('JP', 'Japan'), ('JE', 'Jersey'), ('JO', 'Jordan'),
    ('KZ', 'Kazakhstan'), ('KE', 'Kenya'), ('KI', 'Kiribati'), ('KP', 'Korea (North)'), ('KR', 'Korea (South)'),
    ('KW', 'Kuwait'), ('KG', 'Kyrgyzstan'), ('LA', 'Laos'), ('LV', 'Latvia'), ('LB', 'Lebanon'),
    ('LS', 'Lesotho'), ('LR', 'Liberia'), ('LY', 'Libya'), ('LI', 'Liechtenstein'), ('LT', 'Lithuania'),
    ('LU', 'Luxembourg'), ('MO', 'Macao'), ('MG', 'Madagascar'), ('MW', 'Malawi'), ('MY', 'Malaysia'),
    ('MV', 'Maldives'), ('ML', 'Mali'), ('MT', 'Malta'), ('MH', 'Marshall Islands'), ('MQ', 'Martinique'),
    ('MR', 'Mauritania'), ('MU', 'Mauritius'), ('YT', 'Mayotte'), ('MX', 'Mexico'), ('FM', 'Micronesia'),
    ('MD', 'Moldova'), ('MC', 'Monaco'), ('MN', 'Mongolia'), ('ME', 'Montenegro'), ('MS', 'Montserrat'),
    ('MA', 'Morocco'), ('MZ', 'Mozambique'), ('MM', 'Myanmar'), ('NA', 'Namibia'), ('NR', 'Nauru'),
    ('NP', 'Nepal'), ('NL', 'Netherlands'), ('NC', 'New Caledonia'), ('NZ', 'New Zealand'), ('NI', 'Nicaragua'),
    ('NE', 'Niger'), ('NG', 'Nigeria'), ('NU', 'Niue'), ('NF', 'Norfolk Island'), ('MK', 'North Macedonia'),
    ('MP', 'Northern Mariana Islands'), ('NO', 'Norway'), ('OM', 'Oman'), ('PK', 'Pakistan'), ('PW', 'Palau'),
    ('PS', 'Palestine'), ('PA', 'Panama'), ('PG', 'Papua New Guinea'), ('PY', 'Paraguay'), ('PE', 'Peru'),
    ('PH', 'Philippines'), ('PN', 'Pitcairn'), ('PL', 'Poland'), ('PT', 'Portugal'), ('PR', 'Puerto Rico'),
    ('QA', 'Qatar'), ('RE', 'Réunion'), ('RO', 'Romania'), ('RU', 'Russia'), ('RW', 'Rwanda'),
    ('BL', 'Saint Barthélemy'), ('SH', 'Saint Helena'), ('KN', 'Saint Kitts and Nevis'), ('LC', 'Saint Lucia'), ('MF', 'Saint Martin'),
    ('PM', 'Saint Pierre and Miquelon'), ('VC', 'Saint Vincent and the Grenadines'), ('WS', 'Samoa'), ('SM', 'San Marino'), ('ST', 'Sao Tome and Principe'),
    ('SA', 'Saudi Arabia'), ('SN', 'Senegal'), ('RS', 'Serbia'), ('SC', 'Seychelles'), ('SL', 'Sierra Leone'),
    ('SG', 'Singapore'), ('SX', 'Sint Maarten'), ('SK', 'Slovakia'), ('SI', 'Slovenia'), ('SB', 'Solomon Islands'),
    ('SO', 'Somalia'), ('ZA', 'South Africa'), ('GS', 'South Georgia and the South Sandwich Islands'), ('SS', 'South Sudan'), ('ES', 'Spain'),
    ('LK', 'Sri Lanka'), ('SD', 'Sudan'), ('SR', 'Suriname'), ('SJ', 'Svalbard and Jan Mayen'), ('SE', 'Sweden'),
    ('CH', 'Switzerland'), ('SY', 'Syria'), ('TW', 'Taiwan'), ('TJ', 'Tajikistan'), ('TZ', 'Tanzania'),
    ('TH', 'Thailand'), ('TL', 'Timor-Leste'), ('TG', 'Togo'), ('TK', 'Tokelau'), ('TO', 'Tonga'),
    ('TT', 'Trinidad and Tobago'), ('TN', 'Tunisia'), ('TR', 'Turkey'), ('TM', 'Turkmenistan'), ('TC', 'Turks and Caicos Islands'),
    ('TV', 'Tuvalu'), ('UG', 'Uganda'), ('UA', 'Ukraine'), ('AE', 'United Arab Emirates'), ('GB', 'United Kingdom'),
    ('US', 'United States'), ('UM', 'U.S. Outlying Islands'), ('UY', 'Uruguay'), ('UZ', 'Uzbekistan'), ('VU', 'Vanuatu'),
    ('VE', 'Venezuela'), ('VN', 'Viet Nam'), ('VG', 'Virgin Islands (British)'), ('VI', 'Virgin Islands (U.S.)'), ('WF', 'Wallis and Futuna'),
    ('EH', 'Western Sahara'), ('YE', 'Yemen'), ('ZM', 'Zambia'), ('ZW', 'Zimbabwe'),
]

def upsert_countries():
    app = create_app('development')
    with app.app_context():
        inserted = 0
        for code, name in COUNTRIES:
            code = (code or '').upper()
            name = (name or '').strip()
            if not code or not name:
                continue

            existing = Location.query.filter_by(code=code).first()
            if existing is None:
                db.session.add(Location(code=code, name=name))
                inserted += 1

        db.session.commit()
        print(f'Seeded countries; inserted {inserted} new entries')

if __name__ == '__main__':
    upsert_countries()
