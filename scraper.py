from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
import re
import datetime
import json

app = Flask(__name__)

def APify(num_string):
  num_string = str(num_string)
  nums = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}
  if len(num_string) == 1:
    num_string = nums[num_string]
  return num_string

def get_daily_change(column_name, today_data):
  r = requests.get("https://minnpost-google-sheet-to-json.herokuapp.com/parser/?spreadsheet_id=121YfyOnxak30lhjdVZCaIE40LBZdamIT1nxev8z3Ck4&worksheet_names=daily")
  data = r.json()["daily"]
  previous_total = int(data[-1][column_name])
  if  previous_total == today_data:
    previous_total = int(data[-2][column_name]) #use previous row if current row equals today (spreadsheet already up to date)
  return today_data - previous_total

def scrape_spreadsheet_row():
  r = requests.get("https://www.health.state.mn.us/diseases/coronavirus/situation.html")
  text = r.text
  soup = BeautifulSoup(text, "html.parser")

  #total cases
  casetotal_table = soup.find(id="casetotal")
  cells = casetotal_table.find_all("td")
  total_cases = int(cells[0].get_text().strip().replace(",",""))

  #new deaths
  dailydeathtotal_table = soup.find(id="dailydeathtotal")
  cells = dailydeathtotal_table.find_all("td")
  new_deaths = int(cells[0].get_text().strip().replace(",",""))

  #long term care deaths
  new_ltc_deaths = 0
  ltc_re = re.compile("Long-term [Cc]are [Ff]acility/Assisted [Ll]iving")
  death_residence_table = soup.find(id="dailydeathrt")
  if death_residence_table:
    rows = death_residence_table.find_all("tr")
    for row in rows[1:]:
      cells = row.find_all("td")
      if cells:
        if ltc_re.match(cells[0].get_text()):
          new_ltc_deaths = int(cells[1].get_text().strip().replace(",",""))

  #total deaths
  death_table = soup.find(id="deathtotal")
  rows = death_table.find_all("tr")
  total_deaths = int(rows[0].find_all("td")[0].get_text().strip().replace(",", ""))

  #total tests
  testtotal_table = soup.find(id="testtotal")
  cells = testtotal_table.find_all("td")
  total_tests = int(cells[0].get_text().strip().replace(",",""))

  #new cases
  new_cases = get_daily_change("totalcases", total_cases)

  #new tests
  new_tests = get_daily_change("tests-total", total_tests)

  #date and time
  date = datetime.datetime.now().strftime("%-m/%-d/%Y")
  time = datetime.datetime.now().strftime("%-I:%M %p")

  return {"total_cases": total_cases, "new_deaths": new_deaths, "new_ltc_deaths": new_ltc_deaths, "total_deaths": total_deaths, "total_tests": total_tests, "new_cases": new_cases, "new_tests": new_tests, "date": date, "time": time}

def scrape_full_test_history():
  r = requests.get("https://www.health.state.mn.us/diseases/coronavirus/situation.html")
  text = r.text
  soup = BeautifulSoup(text, "html.parser")

  new_tests_by_day = []

  test_history_table = soup.find(id="labtable")
  rows = test_history_table.find_all("tr")
  previous_day_total = int(rows[1].find_all("td")[-1].get_text().strip().replace(",",""))

  for row in rows[2:]: #skip header row and first row of data
    cells = row.find_all("td")
    if cells[0].get_text().strip() == "Unknown/missing": #Ignore the unknown/missing row for test date table
      continue
    raw_date = cells[0].get_text().strip().split("/")
    month = raw_date[0]
    day = raw_date[1]
    year = "20" + raw_date[2]

    data_received_date = datetime.date(year=int(year), month=int(month), day=int(day))
    data_reported_date = data_received_date + datetime.timedelta(days=1)

    formatted_date = "{}-{}-{}".format(data_reported_date.year, data_reported_date.month, data_reported_date.day)
    
    total_tests = int(cells[-1].get_text().strip().replace(",",""))
    new_tests = total_tests - previous_day_total

    previous_day_total = total_tests

    new_tests_by_day.append([formatted_date, new_tests])

  return new_tests_by_day

def scrape_daily_county_totals():
  r = requests.get("https://www.health.state.mn.us/diseases/coronavirus/situation.html")
  text = r.text
  soup = BeautifulSoup(text, "html.parser")

  county_data = {}

  county_id = {"Aitkin": "aitkin", "Anoka": "anoka", "Becker": "becker", "Beltrami": "beltrami", "Benton": "benton", "Big Stone": "bigstone", "Blue Earth": "blueearth", "Brown": "brown", "Carlton": "carlton", "Carver": "carver", "Cass": "cass", "Chippewa": "chippewa", "Chisago": "chisago", "Clay": "clay", "Clearwater": "clearwater", "Cook": "cook", "Cottonwood": "cottonwood", "Crow Wing": "crowwing", "Dakota": "dakota", "Dodge": "dodge", "Douglas": "douglas", "Faribault": "faribault", "Fillmore": "fillmore", "Freeborn": "freeborn", "Goodhue": "goodhue", "Grant": "grant", "Hennepin": "hennepin", "Houston": "houston", "Hubbard": "hubbard", "Isanti": "isanti", "Itasca": "itasca", "Jackson": "jackson", "Kanabec": "kanabec", "Kandiyohi": "kandiyohi", "Kittson": "kittson", "Koochiching": "koochiching", "Lac qui Parle": "lacquiparle", "Lake": "lake", "Lake of the Woods": "lakeofthewoods", "Lake of the    Woods": "lakeofthewoods", "Le Sueur": "lesueur", "Lincoln": "lincoln", "Lyon": "lyon", "McLeod": "mcleod", "Mahnomen": "mahnomen", "Marshall": "marshall", "Martin": "martin", "Meeker": "meeker", "Mille Lacs": "millelacs", "Morrison": "morrison", "Mower": "mower", "Murray": "murray", "Nicollet": "nicollet", "Nobles": "nobles", "Norman": "norman", "Olmsted": "olmsted", "Otter Tail": "ottertail", "Pennington": "pennington", "Pine": "pine", "Pipestone": "pipestone", "Polk": "polk", "Pope": "pope", "Ramsey": "ramsey", "Red Lake": "redlake", "Redwood": "redwood", "Renville": "renville", "Rice": "rice", "Rock": "rock", "Roseau": "roseau", "St. Louis": "saintlouis", "Scott": "scott", "Sherburne": "sherburne", "Sibley": "sibley", "Stearns": "stearns", "Steele": "steele", "Stevens": "stevens", "Swift": "swift", "Todd": "todd", "Traverse": "traverse", "Wabasha": "wabasha", "Wadena": "wadena", "Waseca": "waseca", "Washington": "washington", "Watonwan": "watonwan", "Wilkin": "wilkin", "Winona": "winona", "Wright": "wright", "Yellow Medicine": "yellowmedicine", "Unknown/missing": "unknown"}

  county_table = soup.find(id="maptable")
  rows = county_table.find_all("tr")
  for row in rows[1:]: #skipping header row
    cells = row.find_all("td")
    county = county_id[cells[0].get_text().strip().replace("    "," ")]
    cases = int(cells[1].get_text().strip().replace(",",""))
    county_data[county] = cases

  return county_data

def were_was(num):
  if num == 1:
    return "was"
  return "were"

def format_ages_sentence_fragment(age_groups):
  age_order = ["100","90","80","70","60","50","40","30","20","10"]
  s = ""
  sentence_parts = []
  for age in age_order:
    for group in age_groups:
      if age == group:
        if age == "100":
          sentence_parts.append("{} {} over 100 years old".format(APify(age_groups[group]), were_was(age_groups[group])))
        else:
          sentence_parts.append("{} {} in their {}s".format(APify(age_groups[group]), were_was(age_groups[group]), age))
  if len(sentence_parts) > 1:
    s += ", ".join(sentence_parts[0:-1])
    s += " and " + sentence_parts[-1]
  elif len(sentence_parts) == 1:
    s = sentence_parts[0]
  else:
    s = ""
  return s

def scrape_death_ages():
  r = requests.get("https://www.health.state.mn.us/diseases/coronavirus/situation.html")
  text = r.text
  soup = BeautifulSoup(text, "html.parser")

  deaths_by_age_decade = {}

  new_deaths_table = soup.find(id="dailydeathar")
  if new_deaths_table:
    rows = new_deaths_table.find_all("tr")

    decade_re = re.compile("(\d?\d)\d")

    for row in rows[1:]: #skipping header row
      cells = row.find_all("td")
      age_range = cells[1].get_text().strip()
      decade = decade_re.match(age_range).group(0)[:-1]+"0"
      count = cells[2].get_text().strip().replace(",","")
      if decade in deaths_by_age_decade:
        deaths_by_age_decade[decade] += int(count)
      else:
        deaths_by_age_decade[decade] = int(count)
  return deaths_by_age_decade

@app.route("/spreadsheet")
def spreadsheet_row():
  return render_template("spreadsheet-row.html", data = scrape_spreadsheet_row())

@app.route("/daily-test-data")
def daily_test_data():
  return json.dumps(scrape_full_test_history())

@app.route("/county-data")
def get_county_data():
  return json.dumps(scrape_daily_county_totals())

@app.route("/daily-update")
def daily_update():
  data = scrape_spreadsheet_row()
  data["new_tests"] = scrape_full_test_history()[-1][1]
  data["date"] = datetime.datetime.now().strftime("%B %-d")
  data["day_of_week"] = datetime.datetime.now().strftime("%A")
  yesterday = datetime.date.today() - datetime.timedelta(days=1)
  data["yesterday_of_week"] = yesterday.strftime("%A")
  data["age_groups_sentence_fragment"] = format_ages_sentence_fragment(scrape_death_ages())
  for k in data: #add commas to numbers
    if isinstance(data[k], int):
      data[k] = "{:,}".format(data[k]) 
  return render_template("update-new.html", data=data)

if __name__ == '__main__':
  app.run()