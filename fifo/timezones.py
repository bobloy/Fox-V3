"""
Timezone information for the dateutil parser

All credit to https://github.com/prefrontal/dateutil-parser-timezones
"""

# from dateutil.tz import gettz
from datetime import datetime

from pytz import timezone


def assemble_timezones():
    """
    Assembles a dictionary of timezone abbreviations and values
    :return: Dictionary of abbreviation keys and timezone values
    """
    timezones = {}

    timezones["ACDT"] = timezone(
        "Australia/Darwin"
    )  # Australian Central Daylight Savings Time (UTC+10:30)
    timezones["ACST"] = timezone(
        "Australia/Darwin"
    )  # Australian Central Standard Time (UTC+09:30)
    timezones["ACT"] = timezone("Brazil/Acre")  # Acre Time (UTC−05)
    timezones["ADT"] = timezone("America/Halifax")  # Atlantic Daylight Time (UTC−03)
    timezones["AEDT"] = timezone(
        "Australia/Sydney"
    )  # Australian Eastern Daylight Savings Time (UTC+11)
    timezones["AEST"] = timezone("Australia/Sydney")  # Australian Eastern Standard Time (UTC+10)
    timezones["AFT"] = timezone("Asia/Kabul")  # Afghanistan Time (UTC+04:30)
    timezones["AKDT"] = timezone("America/Juneau")  # Alaska Daylight Time (UTC−08)
    timezones["AKST"] = timezone("America/Juneau")  # Alaska Standard Time (UTC−09)
    timezones["AMST"] = timezone("America/Manaus")  # Amazon Summer Time (Brazil)[1] (UTC−03)
    timezones["AMT"] = timezone("America/Manaus")  # Amazon Time (Brazil)[2] (UTC−04)
    timezones["ART"] = timezone("America/Cordoba")  # Argentina Time (UTC−03)
    timezones["AST"] = timezone("Asia/Riyadh")  # Arabia Standard Time (UTC+03)
    timezones["AWST"] = timezone("Australia/Perth")  # Australian Western Standard Time (UTC+08)
    timezones["AZOST"] = timezone("Atlantic/Azores")  # Azores Summer Time (UTC±00)
    timezones["AZOT"] = timezone("Atlantic/Azores")  # Azores Standard Time (UTC−01)
    timezones["AZT"] = timezone("Asia/Baku")  # Azerbaijan Time (UTC+04)
    timezones["BDT"] = timezone("Asia/Brunei")  # Brunei Time (UTC+08)
    timezones["BIOT"] = timezone("Etc/GMT-6")  # British Indian Ocean Time (UTC+06)
    timezones["BIT"] = timezone("Etc/GMT+12")  # Baker Island Time (UTC−12)
    timezones["BOT"] = timezone("America/La_Paz")  # Bolivia Time (UTC−04)
    timezones["BRST"] = timezone("America/Sao_Paulo")  # Brasilia Summer Time (UTC−02)
    timezones["BRT"] = timezone("America/Sao_Paulo")  # Brasilia Time (UTC−03)
    timezones["BST"] = timezone("Asia/Dhaka")  # Bangladesh Standard Time (UTC+06)
    timezones["BTT"] = timezone("Asia/Thimphu")  # Bhutan Time (UTC+06)
    timezones["CAT"] = timezone("Africa/Harare")  # Central Africa Time (UTC+02)
    timezones["CCT"] = timezone("Indian/Cocos")  # Cocos Islands Time (UTC+06:30)
    timezones["CDT"] = timezone(
        "America/Chicago"
    )  # Central Daylight Time (North America) (UTC−05)
    timezones["CEST"] = timezone(
        "Europe/Berlin"
    )  # Central European Summer Time (Cf. HAEC) (UTC+02)
    timezones["CET"] = timezone("Europe/Berlin")  # Central European Time (UTC+01)
    timezones["CHADT"] = timezone("Pacific/Chatham")  # Chatham Daylight Time (UTC+13:45)
    timezones["CHAST"] = timezone("Pacific/Chatham")  # Chatham Standard Time (UTC+12:45)
    timezones["CHOST"] = timezone("Asia/Choibalsan")  # Choibalsan Summer Time (UTC+09)
    timezones["CHOT"] = timezone("Asia/Choibalsan")  # Choibalsan Standard Time (UTC+08)
    timezones["CHST"] = timezone("Pacific/Guam")  # Chamorro Standard Time (UTC+10)
    timezones["CHUT"] = timezone("Pacific/Chuuk")  # Chuuk Time (UTC+10)
    timezones["CIST"] = timezone("Etc/GMT+8")  # Clipperton Island Standard Time (UTC−08)
    timezones["CIT"] = timezone("Asia/Makassar")  # Central Indonesia Time (UTC+08)
    timezones["CKT"] = timezone("Pacific/Rarotonga")  # Cook Island Time (UTC−10)
    timezones["CLST"] = timezone("America/Santiago")  # Chile Summer Time (UTC−03)
    timezones["CLT"] = timezone("America/Santiago")  # Chile Standard Time (UTC−04)
    timezones["COST"] = timezone("America/Bogota")  # Colombia Summer Time (UTC−04)
    timezones["COT"] = timezone("America/Bogota")  # Colombia Time (UTC−05)
    timezones["CST"] = timezone(
        "America/Chicago"
    )  # Central Standard Time (North America) (UTC−06)
    timezones["CT"] = timezone("Asia/Chongqing")  # China time (UTC+08)
    timezones["CVT"] = timezone("Atlantic/Cape_Verde")  # Cape Verde Time (UTC−01)
    timezones["CXT"] = timezone("Indian/Christmas")  # Christmas Island Time (UTC+07)
    timezones["DAVT"] = timezone("Antarctica/Davis")  # Davis Time (UTC+07)
    timezones["DDUT"] = timezone("Antarctica/DumontDUrville")  # Dumont d'Urville Time (UTC+10)
    timezones["DFT"] = timezone(
        "Europe/Berlin"
    )  # AIX equivalent of Central European Time (UTC+01)
    timezones["EASST"] = timezone("Chile/EasterIsland")  # Easter Island Summer Time (UTC−05)
    timezones["EAST"] = timezone("Chile/EasterIsland")  # Easter Island Standard Time (UTC−06)
    timezones["EAT"] = timezone("Africa/Mogadishu")  # East Africa Time (UTC+03)
    timezones["ECT"] = timezone("America/Guayaquil")  # Ecuador Time (UTC−05)
    timezones["EDT"] = timezone(
        "America/New_York"
    )  # Eastern Daylight Time (North America) (UTC−04)
    timezones["EEST"] = timezone("Europe/Bucharest")  # Eastern European Summer Time (UTC+03)
    timezones["EET"] = timezone("Europe/Bucharest")  # Eastern European Time (UTC+02)
    timezones["EGST"] = timezone("America/Scoresbysund")  # Eastern Greenland Summer Time (UTC±00)
    timezones["EGT"] = timezone("America/Scoresbysund")  # Eastern Greenland Time (UTC−01)
    timezones["EIT"] = timezone("Asia/Jayapura")  # Eastern Indonesian Time (UTC+09)
    timezones["EST"] = timezone(
        "America/New_York"
    )  # Eastern Standard Time (North America) (UTC−05)
    timezones["FET"] = timezone("Europe/Minsk")  # Further-eastern European Time (UTC+03)
    timezones["FJT"] = timezone("Pacific/Fiji")  # Fiji Time (UTC+12)
    timezones["FKST"] = timezone("Atlantic/Stanley")  # Falkland Islands Summer Time (UTC−03)
    timezones["FKT"] = timezone("Atlantic/Stanley")  # Falkland Islands Time (UTC−04)
    timezones["FNT"] = timezone("Brazil/DeNoronha")  # Fernando de Noronha Time (UTC−02)
    timezones["GALT"] = timezone("Pacific/Galapagos")  # Galapagos Time (UTC−06)
    timezones["GAMT"] = timezone("Pacific/Gambier")  # Gambier Islands (UTC−09)
    timezones["GET"] = timezone("Asia/Tbilisi")  # Georgia Standard Time (UTC+04)
    timezones["GFT"] = timezone("America/Cayenne")  # French Guiana Time (UTC−03)
    timezones["GILT"] = timezone("Pacific/Tarawa")  # Gilbert Island Time (UTC+12)
    timezones["GIT"] = timezone("Pacific/Gambier")  # Gambier Island Time (UTC−09)
    timezones["GMT"] = timezone("GMT")  # Greenwich Mean Time (UTC±00)
    timezones["GST"] = timezone("Asia/Muscat")  # Gulf Standard Time (UTC+04)
    timezones["GYT"] = timezone("America/Guyana")  # Guyana Time (UTC−04)
    timezones["HADT"] = timezone("Pacific/Honolulu")  # Hawaii-Aleutian Daylight Time (UTC−09)
    timezones["HAEC"] = timezone("Europe/Paris")  # Heure Avancée d'Europe Centrale (CEST) (UTC+02)
    timezones["HAST"] = timezone("Pacific/Honolulu")  # Hawaii-Aleutian Standard Time (UTC−10)
    timezones["HKT"] = timezone("Asia/Hong_Kong")  # Hong Kong Time (UTC+08)
    timezones["HMT"] = timezone("Indian/Kerguelen")  # Heard and McDonald Islands Time (UTC+05)
    timezones["HOVST"] = timezone("Asia/Hovd")  # Khovd Summer Time (UTC+08)
    timezones["HOVT"] = timezone("Asia/Hovd")  # Khovd Standard Time (UTC+07)
    timezones["ICT"] = timezone("Asia/Ho_Chi_Minh")  # Indochina Time (UTC+07)
    timezones["IDT"] = timezone("Asia/Jerusalem")  # Israel Daylight Time (UTC+03)
    timezones["IOT"] = timezone("Etc/GMT-3")  # Indian Ocean Time (UTC+03)
    timezones["IRDT"] = timezone("Asia/Tehran")  # Iran Daylight Time (UTC+04:30)
    timezones["IRKT"] = timezone("Asia/Irkutsk")  # Irkutsk Time (UTC+08)
    timezones["IRST"] = timezone("Asia/Tehran")  # Iran Standard Time (UTC+03:30)
    timezones["IST"] = timezone("Asia/Kolkata")  # Indian Standard Time (UTC+05:30)
    timezones["JST"] = timezone("Asia/Tokyo")  # Japan Standard Time (UTC+09)
    timezones["KGT"] = timezone("Asia/Bishkek")  # Kyrgyzstan time (UTC+06)
    timezones["KOST"] = timezone("Pacific/Kosrae")  # Kosrae Time (UTC+11)
    timezones["KRAT"] = timezone("Asia/Krasnoyarsk")  # Krasnoyarsk Time (UTC+07)
    timezones["KST"] = timezone("Asia/Seoul")  # Korea Standard Time (UTC+09)
    timezones["LHST"] = timezone("Australia/Lord_Howe")  # Lord Howe Standard Time (UTC+10:30)
    timezones["LINT"] = timezone("Pacific/Kiritimati")  # Line Islands Time (UTC+14)
    timezones["MAGT"] = timezone("Asia/Magadan")  # Magadan Time (UTC+12)
    timezones["MART"] = timezone("Pacific/Marquesas")  # Marquesas Islands Time (UTC−09:30)
    timezones["MAWT"] = timezone("Antarctica/Mawson")  # Mawson Station Time (UTC+05)
    timezones["MDT"] = timezone(
        "America/Denver"
    )  # Mountain Daylight Time (North America) (UTC−06)
    timezones["MEST"] = timezone(
        "Europe/Paris"
    )  # Middle European Summer Time Same zone as CEST (UTC+02)
    timezones["MET"] = timezone("Europe/Berlin")  # Middle European Time Same zone as CET (UTC+01)
    timezones["MHT"] = timezone("Pacific/Kwajalein")  # Marshall Islands (UTC+12)
    timezones["MIST"] = timezone("Antarctica/Macquarie")  # Macquarie Island Station Time (UTC+11)
    timezones["MIT"] = timezone("Pacific/Marquesas")  # Marquesas Islands Time (UTC−09:30)
    timezones["MMT"] = timezone("Asia/Rangoon")  # Myanmar Standard Time (UTC+06:30)
    timezones["MSK"] = timezone("Europe/Moscow")  # Moscow Time (UTC+03)
    timezones["MST"] = timezone(
        "America/Denver"
    )  # Mountain Standard Time (North America) (UTC−07)
    timezones["MUT"] = timezone("Indian/Mauritius")  # Mauritius Time (UTC+04)
    timezones["MVT"] = timezone("Indian/Maldives")  # Maldives Time (UTC+05)
    timezones["MYT"] = timezone("Asia/Kuching")  # Malaysia Time (UTC+08)
    timezones["NCT"] = timezone("Pacific/Noumea")  # New Caledonia Time (UTC+11)
    timezones["NDT"] = timezone("Canada/Newfoundland")  # Newfoundland Daylight Time (UTC−02:30)
    timezones["NFT"] = timezone("Pacific/Norfolk")  # Norfolk Time (UTC+11)
    timezones["NPT"] = timezone("Asia/Kathmandu")  # Nepal Time (UTC+05:45)
    timezones["NST"] = timezone("Canada/Newfoundland")  # Newfoundland Standard Time (UTC−03:30)
    timezones["NT"] = timezone("Canada/Newfoundland")  # Newfoundland Time (UTC−03:30)
    timezones["NUT"] = timezone("Pacific/Niue")  # Niue Time (UTC−11)
    timezones["NZDT"] = timezone("Pacific/Auckland")  # New Zealand Daylight Time (UTC+13)
    timezones["NZST"] = timezone("Pacific/Auckland")  # New Zealand Standard Time (UTC+12)
    timezones["OMST"] = timezone("Asia/Omsk")  # Omsk Time (UTC+06)
    timezones["ORAT"] = timezone("Asia/Oral")  # Oral Time (UTC+05)
    timezones["PDT"] = timezone(
        "America/Los_Angeles"
    )  # Pacific Daylight Time (North America) (UTC−07)
    timezones["PET"] = timezone("America/Lima")  # Peru Time (UTC−05)
    timezones["PETT"] = timezone("Asia/Kamchatka")  # Kamchatka Time (UTC+12)
    timezones["PGT"] = timezone("Pacific/Port_Moresby")  # Papua New Guinea Time (UTC+10)
    timezones["PHOT"] = timezone("Pacific/Enderbury")  # Phoenix Island Time (UTC+13)
    timezones["PKT"] = timezone("Asia/Karachi")  # Pakistan Standard Time (UTC+05)
    timezones["PMDT"] = timezone(
        "America/Miquelon"
    )  # Saint Pierre and Miquelon Daylight time (UTC−02)
    timezones["PMST"] = timezone(
        "America/Miquelon"
    )  # Saint Pierre and Miquelon Standard Time (UTC−03)
    timezones["PONT"] = timezone("Pacific/Pohnpei")  # Pohnpei Standard Time (UTC+11)
    timezones["PST"] = timezone(
        "America/Los_Angeles"
    )  # Pacific Standard Time (North America) (UTC−08)
    timezones["PYST"] = timezone(
        "America/Asuncion"
    )  # Paraguay Summer Time (South America)[7] (UTC−03)
    timezones["PYT"] = timezone("America/Asuncion")  # Paraguay Time (South America)[8] (UTC−04)
    timezones["RET"] = timezone("Indian/Reunion")  # Réunion Time (UTC+04)
    timezones["ROTT"] = timezone("Antarctica/Rothera")  # Rothera Research Station Time (UTC−03)
    timezones["SAKT"] = timezone("Asia/Vladivostok")  # Sakhalin Island time (UTC+11)
    timezones["SAMT"] = timezone("Europe/Samara")  # Samara Time (UTC+04)
    timezones["SAST"] = timezone("Africa/Johannesburg")  # South African Standard Time (UTC+02)
    timezones["SBT"] = timezone("Pacific/Guadalcanal")  # Solomon Islands Time (UTC+11)
    timezones["SCT"] = timezone("Indian/Mahe")  # Seychelles Time (UTC+04)
    timezones["SGT"] = timezone("Asia/Singapore")  # Singapore Time (UTC+08)
    timezones["SLST"] = timezone("Asia/Colombo")  # Sri Lanka Standard Time (UTC+05:30)
    timezones["SRET"] = timezone("Asia/Srednekolymsk")  # Srednekolymsk Time (UTC+11)
    timezones["SRT"] = timezone("America/Paramaribo")  # Suriname Time (UTC−03)
    timezones["SST"] = timezone("Asia/Singapore")  # Singapore Standard Time (UTC+08)
    timezones["SYOT"] = timezone("Antarctica/Syowa")  # Showa Station Time (UTC+03)
    timezones["TAHT"] = timezone("Pacific/Tahiti")  # Tahiti Time (UTC−10)
    timezones["TFT"] = timezone("Indian/Kerguelen")  # Indian/Kerguelen (UTC+05)
    timezones["THA"] = timezone("Asia/Bangkok")  # Thailand Standard Time (UTC+07)
    timezones["TJT"] = timezone("Asia/Dushanbe")  # Tajikistan Time (UTC+05)
    timezones["TKT"] = timezone("Pacific/Fakaofo")  # Tokelau Time (UTC+13)
    timezones["TLT"] = timezone("Asia/Dili")  # Timor Leste Time (UTC+09)
    timezones["TMT"] = timezone("Asia/Ashgabat")  # Turkmenistan Time (UTC+05)
    timezones["TOT"] = timezone("Pacific/Tongatapu")  # Tonga Time (UTC+13)
    timezones["TVT"] = timezone("Pacific/Funafuti")  # Tuvalu Time (UTC+12)
    timezones["ULAST"] = timezone("Asia/Ulan_Bator")  # Ulaanbaatar Summer Time (UTC+09)
    timezones["ULAT"] = timezone("Asia/Ulan_Bator")  # Ulaanbaatar Standard Time (UTC+08)
    timezones["USZ1"] = timezone("Europe/Kaliningrad")  # Kaliningrad Time (UTC+02)
    timezones["UTC"] = timezone("UTC")  # Coordinated Universal Time (UTC±00)
    timezones["UYST"] = timezone("America/Montevideo")  # Uruguay Summer Time (UTC−02)
    timezones["UYT"] = timezone("America/Montevideo")  # Uruguay Standard Time (UTC−03)
    timezones["UZT"] = timezone("Asia/Tashkent")  # Uzbekistan Time (UTC+05)
    timezones["VET"] = timezone("America/Caracas")  # Venezuelan Standard Time (UTC−04)
    timezones["VLAT"] = timezone("Asia/Vladivostok")  # Vladivostok Time (UTC+10)
    timezones["VOLT"] = timezone("Europe/Volgograd")  # Volgograd Time (UTC+04)
    timezones["VOST"] = timezone("Antarctica/Vostok")  # Vostok Station Time (UTC+06)
    timezones["VUT"] = timezone("Pacific/Efate")  # Vanuatu Time (UTC+11)
    timezones["WAKT"] = timezone("Pacific/Wake")  # Wake Island Time (UTC+12)
    timezones["WAST"] = timezone("Africa/Lagos")  # West Africa Summer Time (UTC+02)
    timezones["WAT"] = timezone("Africa/Lagos")  # West Africa Time (UTC+01)
    timezones["WEST"] = timezone("Europe/London")  # Western European Summer Time (UTC+01)
    timezones["WET"] = timezone("Europe/London")  # Western European Time (UTC±00)
    timezones["WIT"] = timezone("Asia/Jakarta")  # Western Indonesian Time (UTC+07)
    timezones["WST"] = timezone("Australia/Perth")  # Western Standard Time (UTC+08)
    timezones["YAKT"] = timezone("Asia/Yakutsk")  # Yakutsk Time (UTC+09)
    timezones["YEKT"] = timezone("Asia/Yekaterinburg")  # Yekaterinburg Time (UTC+05)

    dt = datetime(2020, 1, 1)
    timezones.update((x, y.localize(dt).tzinfo) for x, y in timezones.items())
    return timezones
