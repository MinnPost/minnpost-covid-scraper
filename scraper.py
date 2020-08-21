from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
import re
import datetime

app = Flask(__name__)

decades_crosswalk = {"0-4 years": "0-9 years", "5-9 years": "0-9 years", "10-14 years": "10-19 years", "15-19 years": "10-19 years", "20-24 years": "20-29 years", "25-29 years": "20-29 years", "30-34 years": "30-39 years", "35-39 years": "30-39 years", "40-44 years": "40-49 years", "45-49 years": "40-49 years", "50-54 years": "50-59 years", "55-59 years": "50-59 years", "60-64 years": "60-69 years", "65-69 years": "60-69 years", "70-74 years": "70-79 years", "75-79 years": "70-79 years", "80-84 years": "80-89 years", "85-89 years": "80-89 years", "90-94 years": "90-99 years", "95-99 years": "90-99 years", "100+ years": "100+ years"}

def APify(num_string):
  num_string = str(num_string)
  nums = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine"}
  if len(num_string) == 1:
    num_string = nums[num_string]
  return num_string

def scrape_covid_data():
  r = requests.get("https://www.health.state.mn.us/diseases/coronavirus/situation.html")
  text = r.text
  soup = BeautifulSoup(text, "html.parser")

  #Get total cases and new deaths
  daily_table = soup.find(id="daily")
  daily_table_entries = daily_table.find_all("td")
  total_cases = daily_table_entries[0].find_all("strong")[0].get_text().strip()
  deaths = daily_table_entries[2].find_all("strong")[0].get_text().strip()

  #Get deaths by age group
  deaths_by_age = {}
  daily_deaths_table = soup.find(id="dailydeathar")
  for row in daily_deaths_table.find_all("tr"):
    entries = row.find_all("td")
    if entries:
      age_range = decades_crosswalk[entries[1].get_text().strip()]
      death_count = int(entries[2].get_text().strip())
      if age_range in deaths_by_age:
        deaths_by_age[age_range] += death_count
      else:
        deaths_by_age[age_range] = death_count

  #Get new deaths in long term care
  new_ltc_deaths = "??"
  death_details_table = soup.find(id="dailydeathrt")
  for row in death_details_table.find_all("tr"):
    cells = row.find_all("td")
    if cells:
      if cells[0].get_text() == "Long-term care facility/Assisted living":
        new_ltc_deaths = cells[1].get_text()

  #get latest test data
  testing_details_table = soup.find(id="labtable")
  rows = testing_details_table.find_all("tr")
  cells = rows[-1].find_all("td")
  mdhtests = cells[1].get_text().strip()
  privatetests = cells[2].get_text().strip()
  totaltests = cells[3].get_text().strip()
  dailytests = int(mdhtests.replace(",","")) + int(privatetests.replace(",",""))
  dailytests = "{:,}".format(dailytests)

  #get all hospital data
  hospital_details_table = soup.find(id="hosptable")
  rows = hospital_details_table.find_all("tr")
  cells = rows[-1].find_all("td")
  icu = cells[0].get_text()
  non_icu = cells[1].get_text()
  current_hospital = "{:,}".format(int(icu.replace(",","")) + int(non_icu.replace(",","")))
  total_hospital = cells[2].get_text()

  #get all the list items so we can try to find specific info
  list_items = soup.find_all("li")

  deaths_re = r"Deaths:"
  deaths_ltc_re = r"Deaths among cases that resided in long-term care or assisted living facilities:"
  recovered_re = r"Patients no longer needing isolation:"
  number_re = r"([\d,]+)"

  for item in list_items:
    t = item.get_text()
    if re.match(deaths_re, t):
      total_deaths = re.findall(number_re, t)[0]
    if re.match(deaths_ltc_re, t):
      total_ltc_deaths = re.findall(number_re, t)[0]
    if re.match(recovered_re, t):
      recovered = re.findall(number_re, t)[0]

  return {
    "total_cases": total_cases,
    "new_deaths": deaths,
    "total_deaths": total_deaths,
    "new_ltc_deaths": new_ltc_deaths,
    "total_ltc_deaths": total_ltc_deaths,
    "deaths_by_age": deaths_by_age,
    "mdh_tests": mdhtests,
    "private_tests": privatetests,
    "daily_tests": dailytests,
    "total_tests": totaltests,
    "hospital_total": total_hospital,
    "hospital_current": current_hospital,
    "hospital_icu": icu,
    "hospital_non_icu": non_icu,
    "recovered": recovered
  }

def get_daily_new_cases(total_cases):
  total_cases = int(total_cases.replace(",",""))
  r = requests.get("https://spreadsheets.google.com/feeds/list/121YfyOnxak30lhjdVZCaIE40LBZdamIT1nxev8z3Ck4/1/public/full?alt=json")
  data = r.json()
  previous_total = int(data["feed"]["entry"][-1]['gsx$totalcases']['$t'])
  if  previous_total == total_cases: #if the last row is equal to the scraped row, the spreadsheets been updated and we should use the previous row
    previous_total = int(data["feed"]["entry"][-2]['gsx$totalcases']['$t'])
  return "{:,}".format(total_cases - previous_total)

def were_was(num):
  if num == 1:
    return "was"
  return "were"

def format_ages_sentence(age_groups, day_of_week):
  s = "Of the people whose deaths were announced {}, ".format(day_of_week)
  age_order = ["100","90","80","70","60","50","40","30","20"]
  sentence_parts = []
  for age in age_order:
    for group in age_groups:
      if age in group:
        if age == "100":
          sentence_parts.append("{} {} over 100 years old".format(APify(age_groups[group]), were_was(age_groups[group])))
        else:
          sentence_parts.append("{} {} in their {}s".format(APify(age_groups[group]), were_was(age_groups[group]), age))
  s += ", ".join(sentence_parts[0:-1])
  s += " and " + sentence_parts[-1]
  s += "."
  return s
  

@app.route("/daily-update")
def daily_update():
  data = scrape_covid_data()
  # for k in data:
  #   data[k] = APify(data[k])
  data["new_cases"] = get_daily_new_cases(data["total_cases"])
  data["date"] = datetime.datetime.now().strftime("%B %-d")
  data["day_of_week"] = datetime.datetime.now().strftime("%A")
  yesterday = datetime.date.today() - datetime.timedelta(days=1)
  data["yesterday_of_week"] = yesterday.strftime("%A")
  data["age_groups_sentence"] = format_ages_sentence(data["deaths_by_age"], data["day_of_week"])
  return render_template("update.html", data=data)

@app.route("/spreadsheet")
def spreadsheet_row():
  data = scrape_covid_data()
  data["date"] = datetime.datetime.now().strftime("%-m/%-d/%Y")
  data["time"] = datetime.datetime.now().strftime("%-I:%M %p")
  data["new_cases"] = get_daily_new_cases(data["total_cases"])
  for k in data:
    if "," in data[k]:
      data[k] = int(data[k].replace(",",""))
  return render_template("spreadsheet-row.html", data=data)

if __name__ == '__main__':
  app.run()