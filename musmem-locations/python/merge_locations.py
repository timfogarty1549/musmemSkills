import json, os

path = os.path.expanduser("~/workspace/musmem/data/contest_locations.json")

with open(path) as f:
    data = json.load(f)

# New entries extracted from article scraping (sessions 1-2, files 1-50)
new_entries = [
    # --- Session 1: files 1-24 ---
    # Mr America - AAU 1945: already complete in JSON, skip
    # Mr America - AAU 1946: date already in JSON, fill venue/location
    {"contest": "Mr America - AAU", "year": "1946",
     "venue": "Boys' Club", "location": "Detroit, Michigan, USA"},
    {"contest": "Mr America - AAU", "year": "1947",
     "date": "June 28-29, 1947", "venue": "Lane Tech High School Auditorium",
     "location": "Chicago, Illinois, USA"},
    {"contest": "Mr America - AAU", "year": "1948",
     "location": "Los Angeles, California, USA"},
    {"contest": "Mr America - AAU", "year": "1951",
     "date": "June 15-16, 1951", "venue": "Greek Theatre, Griffith Park",
     "location": "Los Angeles, California, USA"},
    {"contest": "Mr America - AAU", "year": "1952",
     "date": "June 27-28, 1952", "location": "New York City, New York, USA"},
    {"contest": "Mr Universe - NABBA", "year": "1952",
     "date": "July 12, 1952", "location": "London, England, UK"},
    {"contest": "Mr America - AAU", "year": "1953",
     "date": "June 5-6, 1953", "venue": "Murat Theater",
     "location": "Indianapolis, Indiana, USA"},
    {"contest": "Mr Universe - NABBA", "year": "1954",
     "date": "June 25-26, 1954", "venue": "Scala Theatre",
     "location": "London, England, UK"},
    # Mr America - AAU 1954: existing JSON has "June 26-27, 1954" — possible conflict, include to detect
    {"contest": "Mr America - AAU", "year": "1954",
     "date": "June 25-26, 1954", "venue": "Greek Theatre",
     "location": "Los Angeles, California, USA"},
    {"contest": "Mr America - AAU", "year": "1955",
     "date": "June 4-5, 1955", "venue": "Masonic Auditorium",
     "location": "Cleveland, Ohio, USA"},
    {"contest": "Mr Universe - NABBA", "year": "1955",
     "date": "June 11, 1955", "venue": "London Palladium",
     "location": "London, England, UK"},
    # --- Session 2: files 25-50 ---
    {"contest": "Mr Universe - NABBA", "year": "1956",
     "venue": "London Palladium", "location": "London, England, UK"},
    {"contest": "Mr America - AAU", "year": "1957",
     "venue": "Peabody Auditorium", "location": "Daytona Beach, Florida, USA"},
    {"contest": "Mr Universe - NABBA", "year": "1957",
     "date": "October 19, 1957", "venue": "London Coliseum",
     "location": "London, England, UK"},
    {"contest": "Universe - Pro - NABBA", "year": "1957",
     "date": "October 19, 1957", "venue": "London Coliseum",
     "location": "London, England, UK"},
    {"contest": "Mr America - AAU", "year": "1958",
     "venue": "Embassy Auditorium", "location": "Los Angeles, California, USA"},
    {"contest": "Mr Universe - NABBA", "year": "1958",
     "venue": "London Coliseum", "location": "London, England, UK"},
    {"contest": "Universe - Pro - NABBA", "year": "1958",
     "venue": "London Coliseum", "location": "London, England, UK"},
    {"contest": "Mr America - AAU", "year": "1959",
     "date": "July 31 - August 1, 1959", "venue": "York Fair Grounds",
     "location": "York, Pennsylvania, USA"},
    {"contest": "Mr Universe - NABBA", "year": "1959",
     "venue": "London Palladium", "location": "London, England, UK"},
    {"contest": "Universe - Pro - NABBA", "year": "1959",
     "venue": "London Palladium", "location": "London, England, UK"},
    {"contest": "Mr Universe - NABBA", "year": "1960",
     "location": "London, England, UK"},
    {"contest": "Universe - Pro - NABBA", "year": "1960",
     "location": "London, England, UK"},
    {"contest": "Mr America - AAU", "year": "1961",
     "venue": "Santa Monica Civic Auditorium",
     "location": "Santa Monica, California, USA"},
    {"contest": "Mr Universe - NABBA", "year": "1961",
     "venue": "Victoria Palace Theatre", "location": "London, England, UK"},
    {"contest": "Universe - Pro - NABBA", "year": "1961",
     "venue": "Victoria Palace Theatre", "location": "London, England, UK"},
    {"contest": "Mr America - AAU", "year": "1962",
     "location": "Detroit, Michigan, USA"},
    {"contest": "Mr Universe - NABBA", "year": "1962",
     "date": "September 29, 1962", "location": "London, England, UK"},
    {"contest": "Universe - Pro - NABBA", "year": "1962",
     "date": "September 29, 1962", "location": "London, England, UK"},
    {"contest": "Junior Mr America - AAU", "year": "1963",
     "date": "June 1, 1963", "venue": "Jefferson High School Auditorium",
     "location": "Columbia, Missouri, USA"},
    {"contest": "Mr America - AAU", "year": "1964",
     "date": "June 13-14, 1964", "location": "Chicago, Illinois, USA"},
    {"contest": "Mr Universe - NABBA", "year": "1964",
     "location": "London, England, UK"},
    {"contest": "Universe - Pro - NABBA", "year": "1964",
     "location": "London, England, UK"},
    {"contest": "Mr America - IFBB", "year": "1964",
     "date": "September 19, 1964", "venue": "Brooklyn Academy of Music",
     "location": "New York City, New York, USA"},
    {"contest": "Universe - IFBB", "year": "1964",
     "date": "September 19, 1964", "venue": "Brooklyn Academy of Music",
     "location": "New York City, New York, USA"},
]

_page25 = [
    # Page 25
    {"contest": "Battle of Texas Pro - IFBB", "year": "2022",
     "date": "December 10, 2022", "location": "Irving, Texas, USA"},
    {"contest": "Big Man Pro - IFBB", "year": "2022",
     "date": "November 27, 2022", "location": "Alicante, Spain"},
    {"contest": "Taiwan Pro - IFBB", "year": "2022",
     "date": "November 27, 2022", "location": "Taiwan"},
    {"contest": "Shawn Ray Hawaiian Classic Pro - IFBB", "year": "2022",
     "date": "November 19, 2022", "location": "Honolulu, Hawaii, USA"},
    {"contest": "Romania Muscle Fest Pro - IFBB", "year": "2022",
     "date": "November 12-13, 2022", "location": "Bucharest, Romania"},
    {"contest": "Sacramento Pro - IFBB", "year": "2022",
     "date": "November 12, 2022", "location": "Sacramento, California, USA"},
    {"contest": "MuscleContest Mercosul Pro - IFBB", "year": "2022",
     "date": "December 12, 2022", "location": "Novo Hamburgo, Brazil"},
    {"contest": "Europa Pro Championships - IFBB", "year": "2022",
     "date": "November 4-6, 2022", "location": "Spain"},
    {"contest": "MuscleContest FitPira Pro - IFBB", "year": "2022",
     "date": "November 6, 2022", "location": "Piracicaba, Brazil"},
]

_page24 = [
    # Page 24
    {"contest": "Houston Tournament of Champions Pro - IFBB", "year": "2023",
     "date": "April 1, 2023", "location": "Houston, Texas, USA"},
    {"contest": "Tri-City Pro - IFBB", "year": "2023",
     "date": "March 31 - April 1, 2023", "location": "Columbus, Georgia, USA"},
    {"contest": "MuscleContest Rio de Janeiro Pro - IFBB", "year": "2023",
     "date": "March 25, 2023", "location": "Rio de Janeiro, Brazil"},
    {"contest": "Sampson Showdown Pro - IFBB", "year": "2023",
     "date": "March 25, 2023", "location": "Las Vegas, Nevada, USA"},
    {"contest": "Klash Series Championships Pro - IFBB", "year": "2023",
     "date": "March 25, 2023", "location": "Orlando, Florida, USA"},
    {"contest": "MuscleContest Campinas Pro - IFBB", "year": "2023",
     "date": "March 18, 2023", "location": "Campinas, Brazil"},
    {"contest": "Orchid Pro - IFBB", "year": "2023",
     "date": "February 25, 2023", "location": "Singapore"},
    {"contest": "Japan Pro - IFBB", "year": "2023",
     "date": "February 18-19, 2023", "location": "Japan"},
    {"contest": "Saudi Arabia Pro - IFBB", "year": "2023",
     "date": "January 14, 2023", "location": "Saudi Arabia"},
]

_page23 = [
    # Page 23
    {"contest": "Florida Grand Prix Masters Pro - IFBB", "year": "2023",
     "date": "May 6, 2023", "location": "Boca Raton, Florida, USA"},
    {"contest": "St. Louis Pro - IFBB", "year": "2023",
     "date": "May 6, 2023", "location": "St. Louis, Missouri, USA"},
    {"contest": "GRL PWR Pro - IFBB", "year": "2023",
     "date": "April 29, 2023", "location": "Orlando, Florida, USA"},
    {"contest": "Emerald Cup Pro - IFBB", "year": "2023",
     "date": "April 28, 2023", "location": "Bellevue, Washington, USA"},
    {"contest": "Vancouver Island Showdown Pro - IFBB", "year": "2023",
     "date": "April 23, 2023", "location": "Victoria, British Columbia, Canada"},
    {"contest": "Charlotte Cup Pro - IFBB", "year": "2023",
     "date": "April 22-23, 2023", "location": "Charlotte, North Carolina, USA"},
    {"contest": "Los Angeles Grand Prix Pro - IFBB", "year": "2023",
     "date": "April 22, 2023", "location": "Anaheim, California, USA"},
    {"contest": "Wasatch Warrior Pro - IFBB", "year": "2023",
     "date": "April 15, 2023", "location": "Salt Lake City, Utah, USA"},
    {"contest": "Memphis Pro - IFBB", "year": "2023",
     "date": "April 8, 2023", "location": "Memphis, Tennessee, USA"},
    {"contest": "1 Bro Pro Show - IFBB", "year": "2023",
     "date": "April 8, 2023", "location": "Maidenhead, United Kingdom"},
    {"contest": "Fitworld Pro - IFBB", "year": "2023",
     "date": "April 1, 2023", "location": "Anaheim, California, USA"},
]

_page22 = [
    # Page 22
    {"contest": "Mile High Pro - IFBB", "year": "2023",
     "date": "June 10, 2023", "location": "Denver, Colorado, USA"},
    {"contest": "DC Pro - IFBB", "year": "2023",
     "date": "June 10, 2023", "location": "Alexandria, Virginia, USA"},
    {"contest": "Toronto Pro Supershow - IFBB", "year": "2023",
     "date": "June 4, 2023", "location": "Toronto, Ontario, Canada"},
    {"contest": "Nevada State Pro - IFBB", "year": "2023",
     "date": "June 3, 2023", "location": "Las Vegas, Nevada, USA"},
    {"contest": "Adela Garcia Pro - IFBB", "year": "2023",
     "date": "June 3, 2023", "location": "Austin, Texas, USA"},
    {"contest": "Omaha Pro - IFBB", "year": "2023",
     "date": "June 3, 2023", "location": "Omaha, Nebraska, USA"},
    {"contest": "Miami Muscle Beach Pro - IFBB", "year": "2023",
     "date": "June 3, 2023", "location": "Miami Beach, Florida, USA"},
    {"contest": "Klash Series Southern USA Pro - IFBB", "year": "2023",
     "date": "May 27, 2023", "location": "Orlando, Florida, USA"},
    {"contest": "California State Pro - IFBB", "year": "2023",
     "date": "May 27, 2023", "location": "San Diego, California, USA"},
    {"contest": "Palmetto Classic Pro - IFBB", "year": "2023",
     "date": "May 27, 2023", "location": "Columbia, South Carolina, USA"},
    {"contest": "Junior USA Championships - NPC", "year": "2023",
     "date": "May 19, 2023"},
    {"contest": "Optimum Classic Pro - IFBB", "year": "2023",
     "date": "May 20, 2023", "location": "Shreveport, Louisiana, USA"},
    {"contest": "California Night of Champions Pro - IFBB", "year": "2023",
     "date": "May 13, 2023", "location": "San Diego, California, USA"},
]

_page21 = [
    # Page 21
    {"contest": "Republic of Texas Pro - IFBB", "year": "2023",
     "date": "July 8, 2023", "location": "Austin, Texas, USA"},
    {"contest": "Taiwan Pro - IFBB", "year": "2023",
     "date": "June 30 - July 2, 2023", "location": "Kaohsiung, Taiwan"},
    {"contest": "Orlando Pro - IFBB", "year": "2023",
     "date": "July 1, 2023", "location": "Orlando, Florida, USA"},
    {"contest": "Sheru Classic Italy Pro - IFBB", "year": "2023",
     "date": "June 25, 2023", "location": "Milan, Italy"},
    {"contest": "Empro Pro - IFBB", "year": "2023",
     "date": "June 18, 2023", "location": "Alicante, Spain"},
    {"contest": "Dallas Pro - IFBB", "year": "2023",
     "date": "June 17, 2023", "location": "Dallas, Texas, USA"},
    {"contest": "AGP Pro - IFBB", "year": "2023",
     "date": "June 17, 2023", "location": "South Korea"},
    {"contest": "Northern California Pro - IFBB", "year": "2023",
     "date": "June 10, 2023", "location": "Sacramento, California, USA"},
]

_page20 = [
    # Page 20
    {"contest": "Big Man Pro - IFBB", "year": "2023",
     "date": "July 29, 2023", "location": "Benidorm, Spain"},
    {"contest": "USA Championships - NPC", "year": "2023",
     "date": "July 28, 2023"},
    {"contest": "Vancouver Pro - IFBB", "year": "2023",
     "date": "July 14-16, 2023", "location": "Vancouver, British Columbia, Canada"},
    {"contest": "AGP Bikini Pro - IFBB", "year": "2023",
     "date": "July 15, 2023", "location": "South Korea"},
    {"contest": "Lenda Murray Atlanta Pro - IFBB", "year": "2023",
     "date": "July 15-16, 2023", "location": "Atlanta, Georgia, USA"},
    {"contest": "Mr. Big Evolution Portugal Pro - IFBB", "year": "2023",
     "date": "July 9, 2023", "location": "Portugal"},
    {"contest": "Patriots Challenge Pro - IFBB", "year": "2023",
     "date": "July 8, 2023", "location": "Las Vegas, Nevada, USA"},
]

_page19 = [
    # Page 19
    {"contest": "RGV Classic Pro - IFBB", "year": "2023",
     "date": "September 2, 2023", "location": "McAllen, Texas, USA"},
    {"contest": "MuscleContest Iron Games Pro - IFBB", "year": "2023",
     "date": "September 2, 2023", "location": "Anaheim, California, USA"},
    {"contest": "Nashville FitShow Pro - IFBB", "year": "2023",
     "date": "August 19, 2023", "location": "Nashville, Tennessee, USA"},
    {"contest": "Pacific USA Pro - IFBB", "year": "2023",
     "date": "August 12, 2023", "location": "San Diego, California, USA"},
]

_page18 = [
    # Page 18
    {"contest": "Daytona Pro - IFBB", "year": "2023",
     "date": "September 29, 2023", "location": "Daytona Beach, Florida, USA"},
    {"contest": "Heart of Texas Pro - IFBB", "year": "2023",
     "date": "September 9, 2023", "location": "Dallas, Texas, USA"},
    {"contest": "Battle of the Bodies Pro - IFBB", "year": "2023",
     "date": "September 16, 2023", "location": "Fort Lauderdale, Florida, USA"},
    {"contest": "Legion Masters Pro - IFBB", "year": "2023",
     "date": "October 7, 2023", "location": "Reno, Nevada, USA"},
    {"contest": "Legion Pro - IFBB", "year": "2023",
     "date": "October 8, 2023", "location": "Reno, Nevada, USA"},
    {"contest": "Masters World Championships - IFBB", "year": "2023",
     "date": "September 3, 2023", "location": "Pittsburgh, Pennsylvania, USA"},
    {"contest": "Mr. & Ms. Lions Classic Grand Battle Pro - IFBB", "year": "2023",
     "date": "October 14, 2023", "location": "Guadalajara, Mexico"},
    {"contest": "San Antonio Pro - IFBB", "year": "2023",
     "date": "September 23, 2023", "location": "San Antonio, Texas, USA"},
    {"contest": "Sasquatch Pro - IFBB", "year": "2023",
     "date": "September 9, 2023", "location": "Federal Way, Washington, USA"},
    {"contest": "Sheru Classic France Pro - IFBB", "year": "2023",
     "date": "September 28-29, 2023", "location": "France"},
    {"contest": "Southern Muscle Showdown Pro - IFBB", "year": "2023",
     "date": "October 7, 2023", "location": "Dalton, Georgia, USA"},
    {"contest": "Ultimate Grand Prix Masters Pro - IFBB", "year": "2023",
     "date": "October 14, 2023", "location": "Boca Raton, Florida, USA"},
    {"contest": "Van City Showdown Pro - IFBB", "year": "2023",
     "date": "September 30, 2023", "location": "Burnaby, British Columbia, Canada"},
    {"contest": "MuscleContest Vietnam Pro - IFBB", "year": "2023",
     "date": "October 13, 2023", "location": "Vietnam"},
]

_page17 = [
    # Page 17
    {"contest": "Shawn Ray Hawaiian Classic Pro - IFBB", "year": "2023",
     "date": "November 18, 2023", "location": "Honolulu, Hawaii, USA"},
    {"contest": "Sheru Classic India Pro - IFBB", "year": "2023",
     "date": "November 17-19, 2023", "location": "Mumbai, India"},
    {"contest": "Romania Muscle Fest Pro - IFBB", "year": "2023",
     "date": "November 11, 2023", "location": "Bucharest, Romania"},
    {"contest": "Korea Pro - IFBB", "year": "2023",
     "date": "November 11, 2023", "location": "South Korea"},
    {"contest": "Caribbean Grand Prix Masters Pro - IFBB", "year": "2023",
     "date": "November 11, 2023", "location": "Nassau, Bahamas"},
    {"contest": "Texas State Pro - IFBB", "year": "2023",
     "date": "November 11, 2023", "location": "San Marcos, Texas, USA"},
    {"contest": "Hurricane Pro - IFBB", "year": "2023",
     "date": "October 21, 2023", "location": "St. Petersburg, Florida, USA"},
    {"contest": "Chattanooga Night of Champions Pro - IFBB", "year": "2023",
     "date": "October 21, 2023", "location": "Chattanooga, Tennessee, USA"},
    {"contest": "British Championships Pro - IFBB", "year": "2023",
     "date": "October 14, 2023", "location": "Manchester, United Kingdom"},
]

_page16 = [
    # Page 16
    {"contest": "Taiwan Pro - IFBB", "year": "2024",
     "date": "April 4, 2024", "location": "Kaohsiung, Taiwan"},
    {"contest": "Houston Tournament of Champions Pro - IFBB", "year": "2024",
     "date": "March 30, 2024", "location": "The Woodlands, Texas, USA"},
    {"contest": "Klash Series Championships Pro - IFBB", "year": "2024",
     "date": "March 30, 2024", "location": "Orlando, Florida, USA"},
    {"contest": "San Diego Pro - IFBB", "year": "2024",
     "date": "March 30, 2024", "location": "San Diego, California, USA"},
    {"contest": "Sampson Showdown Pro - IFBB", "year": "2024",
     "date": "March 23, 2024", "location": "Las Vegas, Nevada, USA"},
    {"contest": "MuscleContest Campinas Pro - IFBB", "year": "2024",
     "date": "March 16, 2024", "location": "Campinas, Brazil"},
    {"contest": "National Championships - NPC", "year": "2023",
     "date": "December 9, 2023"},
    {"contest": "Pharlabs Battle of Bogota Pro - IFBB", "year": "2023",
     "date": "November 18-19, 2023", "location": "Bogota, Colombia"},
]

_page15 = [
    # Page 15
    {"contest": "Los Angeles Grand Prix Pro - IFBB", "year": "2024",
     "date": "April 27, 2024", "location": "Anaheim, California, USA"},
    {"contest": "St. Louis Pro - IFBB", "year": "2024",
     "date": "April 27, 2024", "location": "St. Louis, Missouri, USA"},
    {"contest": "Klash Series GRL PWR Pro - IFBB", "year": "2024",
     "date": "April 27, 2024", "location": "Orlando, Florida, USA"},
    {"contest": "Emerald Cup Pro - IFBB", "year": "2024",
     "date": "April 26, 2024", "location": "Bellevue, Washington, USA"},
    {"contest": "Vancouver Island Showdown Pro - IFBB", "year": "2024",
     "date": "April 20, 2024", "location": "Victoria, British Columbia, Canada"},
    {"contest": "Wasatch Warrior Pro - IFBB", "year": "2024",
     "date": "April 20, 2024", "location": "Salt Lake City, Utah, USA"},
    {"contest": "Detroit Pro - IFBB", "year": "2024",
     "date": "April 13, 2024", "location": "Dearborn, Michigan, USA"},
    {"contest": "Tri-City Pro - IFBB", "year": "2024",
     "date": "April 13, 2024", "location": "Columbus, Georgia, USA"},
    {"contest": "Fitworld Pro - IFBB", "year": "2024",
     "date": "April 13, 2024", "location": "Los Angeles, California, USA"},
    {"contest": "Charlotte Cup Pro - IFBB", "year": "2024",
     "date": "April 6, 2024", "location": "Charlotte, North Carolina, USA"},
    {"contest": "Arnold Brazil Pro - IFBB", "year": "2024",
     "date": "April 5, 2024", "location": "Sao Paulo, Brazil"},
    {"contest": "1 Bro Pro Show - IFBB", "year": "2024",
     "date": "April 6, 2024", "location": "London, United Kingdom"},
    {"contest": "Triple O Dynasty Pro - IFBB", "year": "2024",
     "date": "April 6, 2024", "location": "Mesa, Arizona, USA"},
]

_page14 = [
    # Page 14
    {"contest": "German Classic Pro - IFBB", "year": "2024",
     "date": "May 25, 2024", "location": "St. Leon-Rot, Germany"},
    {"contest": "Optimum Classic Pro - IFBB", "year": "2024",
     "date": "May 25, 2024", "location": "Shreveport, Louisiana, USA"},
    {"contest": "California State Pro - IFBB", "year": "2024",
     "date": "May 25, 2024", "location": "Anaheim, California, USA"},
    {"contest": "Klash Series Southern USA Pro - IFBB", "year": "2024",
     "date": "May 25, 2024", "location": "Orlando, Florida, USA"},
    {"contest": "Mexico Pro - IFBB", "year": "2024",
     "date": "May 18, 2024", "location": "Guadalajara, Mexico"},
    {"contest": "New York Pro Championships - IFBB", "year": "2024",
     "date": "May 18, 2024", "location": "Teaneck, New Jersey, USA"},
    {"contest": "Junior USA Championships - NPC", "year": "2024",
     "date": "May 17, 2024"},
    {"contest": "Pittsburgh Pro - IFBB", "year": "2024",
     "date": "May 10, 2024", "location": "Pittsburgh, Pennsylvania, USA"},
    {"contest": "Hungary Kokeny Pro - IFBB", "year": "2024",
     "date": "May 11, 2024", "location": "Budapest, Hungary"},
    {"contest": "AGP Bikini Pro - IFBB", "year": "2024",
     "date": "May 4, 2024", "location": "Paju City, South Korea"},
    {"contest": "AGP Pro - IFBB", "year": "2024",
     "date": "April 28, 2024", "location": "Gyeonggi, South Korea"},
    {"contest": "Dragon Physique DMS Pro - IFBB", "year": "2024",
     "date": "April 28, 2024", "location": "Changsha, China"},
]

_page13 = [
    # Page 13
    {"contest": "South Florida Pro - IFBB", "year": "2024",
     "date": "June 22, 2024", "location": "Boca Raton, Florida, USA"},
    {"contest": "Empro Pro - IFBB", "year": "2024",
     "date": "June 16, 2024", "location": "Alicante, Spain"},
    {"contest": "Dallas Pro - IFBB", "year": "2024",
     "date": "June 15, 2024", "location": "Dallas, Texas, USA"},
    {"contest": "Southern California Championships Pro - IFBB", "year": "2024",
     "date": "June 15, 2024", "location": "San Diego, California, USA"},
    {"contest": "Toronto Pro Supershow - IFBB", "year": "2024",
     "date": "June 9, 2024", "location": "Toronto, Ontario, Canada"},
    {"contest": "Oklahoma Pro - IFBB", "year": "2024",
     "date": "June 8, 2024", "location": "Tulsa, Oklahoma, USA"},
    {"contest": "Omaha Pro - IFBB", "year": "2024",
     "date": "June 8, 2024", "location": "Omaha, Nebraska, USA"},
    {"contest": "DC Pro - IFBB", "year": "2024",
     "date": "June 8, 2024", "location": "Alexandria, Virginia, USA"},
    {"contest": "Adela Garcia Pro - IFBB", "year": "2024",
     "date": "June 8, 2024", "location": "Bastrop, Texas, USA"},
    {"contest": "Mile High Pro - IFBB", "year": "2024",
     "date": "June 8, 2024", "location": "Denver, Colorado, USA"},
    {"contest": "Mid-USA Pro - IFBB", "year": "2024",
     "date": "June 2, 2024", "location": "Albuquerque, New Mexico, USA"},
    {"contest": "Miami Muscle Beach Pro - IFBB", "year": "2024",
     "date": "June 1, 2024", "location": "Miami, Florida, USA"},
    {"contest": "Nevada State Pro - IFBB", "year": "2024",
     "date": "June 1, 2024", "location": "Las Vegas, Nevada, USA"},
]

_page11 = [
    # Page 11
    {"contest": "Tampa Pro - IFBB", "year": "2024",
     "date": "August 1, 2024", "location": "Tampa, Florida, USA"},
    {"contest": "Dubai Pro - IFBB", "year": "2024",
     "date": "July 28, 2024", "location": "Dubai, United Arab Emirates"},
    {"contest": "USA Championships - NPC", "year": "2024",
     "date": "July 26-27, 2024"},
    {"contest": "Colombia Pro - IFBB", "year": "2024",
     "date": "July 18, 2024", "location": "Medellin, Colombia"},
    {"contest": "Teen Collegiate & Masters National Championships - NPC", "year": "2024",
     "date": "July 17-18, 2024"},
    {"contest": "Patriots Challenge Pro - IFBB", "year": "2024",
     "date": "July 20, 2024", "location": "Las Vegas, Nevada, USA"},
    {"contest": "Vancouver Pro - IFBB", "year": "2024",
     "date": "July 13, 2024", "location": "Abbotsford, British Columbia, Canada"},
    {"contest": "Lenda Murray Atlanta Pro - IFBB", "year": "2024",
     "date": "July 13, 2024", "location": "Atlanta, Georgia, USA"},
    {"contest": "Zhanna Rotar Los Angeles Pro - IFBB", "year": "2024",
     "date": "July 13, 2024", "location": "Anaheim, California, USA"},
    {"contest": "Republic of Texas Pro - IFBB", "year": "2024",
     "date": "July 13, 2024", "location": "Austin, Texas, USA"},
]

_page10 = [
    # Page 10
    {"contest": "Arizona Pro - IFBB", "year": "2024",
     "date": "August 24, 2024", "location": "Phoenix, Arizona, USA"},
    {"contest": "Rising Phoenix Pro - IFBB", "year": "2024",
     "date": "August 24, 2024", "location": "Phoenix, Arizona, USA"},
    {"contest": "World Klash Pro - IFBB", "year": "2024",
     "date": "August 24, 2024", "location": "Charleston, South Carolina, USA"},
    {"contest": "Tupelo Pro - IFBB", "year": "2024",
     "date": "August 16, 2024", "location": "Tupelo, Mississippi, USA"},
    {"contest": "Florida State Pro - IFBB", "year": "2024",
     "date": "August 10, 2024", "location": "Orlando, Florida, USA"},
    {"contest": "Pacific USA Pro - IFBB", "year": "2024",
     "date": "August 10, 2024", "location": "San Diego, California, USA"},
]

_page9 = [
    # Page 9
    {"contest": "Daytona Pro - IFBB", "year": "2024",
     "date": "September 28, 2024", "location": "Daytona Beach, Florida, USA"},
    {"contest": "Titans Grand Prix Pro - IFBB", "year": "2024",
     "date": "September 21, 2024", "location": "Anaheim, California, USA"},
    {"contest": "Turkiye Pro - IFBB", "year": "2024",
     "date": "September 19, 2024", "location": "Izmir, Turkey"},
    {"contest": "Europa Pro - IFBB", "year": "2024",
     "date": "September 14, 2024", "location": "London, United Kingdom"},
    {"contest": "Battle of the Bodies Pro - IFBB", "year": "2024",
     "date": "September 14, 2024", "location": "Ft. Lauderdale, Florida, USA"},
    {"contest": "San Antonio Pro - IFBB", "year": "2024",
     "date": "September 14, 2024", "location": "San Antonio, Texas, USA"},
    {"contest": "Pro Muscle Pro - IFBB", "year": "2024",
     "date": "September 8, 2024", "location": "Milan, Italy"},
    {"contest": "Florida Pro - IFBB", "year": "2024",
     "date": "September 7, 2024", "location": "Sarasota, Florida, USA"},
    {"contest": "Heart of Texas Pro - IFBB", "year": "2024",
     "date": "September 7, 2024", "location": "Dallas, Texas, USA"},
    {"contest": "RGV Classic Pro - IFBB", "year": "2024",
     "date": "August 31, 2024", "location": "McAllen, Texas, USA"},
    {"contest": "Masters World Championships - IFBB", "year": "2024",
     "date": "September 1, 2024", "location": "Pittsburgh, Pennsylvania, USA"},
]

_page7 = [
    # Page 7
    {"contest": "Pittsburgh Power & Fitness Pro - IFBB", "year": "2025",
     "date": "May 10, 2025", "location": "Pittsburgh, Pennsylvania, USA"},
    {"contest": "Los Angeles Grand Prix Pro - IFBB", "year": "2025",
     "date": "April 26, 2025", "location": "Anaheim, California, USA"},
    {"contest": "GRL PWR Pro - IFBB", "year": "2025",
     "date": "April 26, 2025", "location": "Orlando, Florida, USA"},
    {"contest": "Huanji China Pro - IFBB", "year": "2025",
     "date": "April 20, 2025", "location": "Shanghai, China"},
    {"contest": "St. Louis Pro - IFBB", "year": "2025",
     "date": "April 19, 2025", "location": "St. Louis, Missouri, USA"},
    {"contest": "1 Bro Pro Show - IFBB", "year": "2025",
     "date": "April 19, 2025", "location": "Maidenhead, United Kingdom"},
    {"contest": "FIBO Pro Championships - IFBB", "year": "2025",
     "date": "April 12, 2025", "location": "Cologne, Germany"},
    {"contest": "Charlotte Cup Pro - IFBB", "year": "2025",
     "date": "April 12, 2025", "location": "Charlotte, North Carolina, USA"},
    {"contest": "Detroit Pro - IFBB", "year": "2025",
     "date": "March 29, 2025", "location": "Dearborn, Michigan, USA"},
    {"contest": "Sampson Showdown Pro - IFBB", "year": "2025",
     "date": "March 29, 2025", "location": "Las Vegas, Nevada, USA"},
    {"contest": "San Diego Pro - IFBB", "year": "2025",
     "date": "March 8, 2025", "location": "San Diego, California, USA"},
    {"contest": "Arnold Classic - IFBB", "year": "2025",
     "date": "February 28 - March 1, 2025", "location": "Columbus, Ohio, USA"},
]

_page8 = [
    # Page 8
    {"contest": "Bharat Pro Show - IFBB", "year": "2024",
     "date": "December 20, 2024", "location": "Mumbai, India"},
    {"contest": "Japan Pro - IFBB", "year": "2024",
     "date": "November 24, 2024", "location": "Tokyo, Japan"},
    {"contest": "Kansas City Pro - IFBB", "year": "2024",
     "date": "November 23, 2024", "location": "Kansas City, Missouri, USA"},
    {"contest": "EVLS Prague Pro - IFBB", "year": "2024",
     "date": "November 16, 2024", "location": "Prague, Czech Republic"},
    {"contest": "Ben Weider Natural Pro - IFBB", "year": "2024",
     "date": "November 15, 2024", "location": "Alexandria, Virginia, USA"},
    {"contest": "Atlantic Coast Pro - IFBB", "year": "2024",
     "date": "November 16, 2024", "location": "Ft. Lauderdale, Florida, USA"},
    {"contest": "Texas State Pro - IFBB", "year": "2024",
     "date": "November 9, 2024", "location": "San Marcos, Texas, USA"},
    {"contest": "Olympia - IFBB", "year": "2024",
     "date": "October 11-12, 2024", "location": "Las Vegas, Nevada, USA"},
    {"contest": "Legion Pro - IFBB", "year": "2024",
     "date": "September 29, 2024", "location": "Reno, Nevada, USA"},
]

# Page 6 (kept for reference)
_page6 = [
    # Page 6
    {"contest": "Spanish Masters Pro - IFBB", "year": "2025",
     "date": "June 8, 2025", "location": "Madrid, Spain"},
    {"contest": "Adela Garcia Pro - IFBB", "year": "2025",
     "date": "June 7, 2025", "location": "Austin, Texas, USA"},
    {"contest": "Oklahoma Pro - IFBB", "year": "2025",
     "date": "June 7, 2025", "location": "Tulsa, Oklahoma, USA"},
    {"contest": "DC Pro - IFBB", "year": "2025",
     "date": "June 7, 2025", "location": "Manassas, Virginia, USA"},
    {"contest": "Mile High Pro - IFBB", "year": "2025",
     "date": "June 7, 2025", "location": "Denver, Colorado, USA"},
    {"contest": "Southern California Championships Pro - IFBB", "year": "2025",
     "date": "June 7, 2025", "location": "San Diego, California, USA"},
    {"contest": "Omaha Pro - IFBB", "year": "2025",
     "date": "June 7, 2025", "location": "Omaha, Nebraska, USA"},
    {"contest": "Thailand Pro - IFBB", "year": "2025",
     "date": "June 7, 2025", "location": "Pattaya, Thailand"},
    {"contest": "Legion Sports Fest Pro - IFBB", "year": "2025",
     "date": "May 31, 2025", "location": "Reno, Nevada, USA"},
    {"contest": "Miami Pro - IFBB", "year": "2025",
     "date": "May 24, 2025", "location": "Miami, Florida, USA"},
    {"contest": "California State Pro - IFBB", "year": "2025",
     "date": "May 24, 2025", "location": "Anaheim, California, USA"},
    {"contest": "New York Pro Championships - IFBB", "year": "2025",
     "date": "May 17, 2025", "location": "Teaneck, New Jersey, USA"},
    {"contest": "Pittsburgh Natural Pro Qualifier - NPC Worldwide", "year": "2025",
     "date": "May 10, 2025"},
]

# Build lookup: contest name (lowered) -> index in data
index = {e["contest"].lower(): i for i, e in enumerate(data)}

added = []
skipped = []
conflicts = []

for entry in new_entries:
    name = entry["contest"]
    year = entry["year"]
    year_data = {k: v for k, v in entry.items() if k not in ("contest", "year") and v}

    idx = index.get(name.lower())
    if idx is not None:
        # Contest exists — check if this year already has data
        existing_year = data[idx]["years"].get(year)
        if existing_year:
            # Compare non-empty fields for conflicts
            diff = {k: (existing_year.get(k), v)
                    for k, v in year_data.items()
                    if existing_year.get(k) and existing_year.get(k) != v}
            if diff:
                conflicts.append(f"CONFLICT: \"{data[idx]['contest']}\" {year} — stored: {existing_year}, extracted: {year_data}")
            else:
                # Fill in any empty fields with new values
                updated = False
                for k, v in year_data.items():
                    if not data[idx]["years"][year].get(k):
                        data[idx]["years"][year][k] = v
                        updated = True
                if updated:
                    added.append(f"UPDATED year {year} in existing \"{data[idx]['contest']}\"")
                else:
                    skipped.append(f"SKIP (matches): \"{data[idx]['contest']}\" {year}")
        else:
            data[idx]["years"][year] = year_data
            added.append(f"ADDED year {year} to existing \"{data[idx]['contest']}\"")
    else:
        # New contest entirely
        data.append({"contest": name, "years": {year: year_data}})
        index[name.lower()] = len(data) - 1
        added.append(f"ADDED new contest \"{name}\" {year}")

with open(path, "w") as f:
    json.dump(data, f, indent=2)

print("\n".join(added))
if skipped:
    print("\n".join(skipped))
if conflicts:
    print("\n".join(conflicts))
print(f"\nDone: {len(added)} added, {len(skipped)} skipped, {len(conflicts)} conflicts")
