from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
import re
import datetime

app = Flask(__name__)

def get_daily_change(column_name, today_data):
  r = requests.get("https://spreadsheets.google.com/feeds/list/121YfyOnxak30lhjdVZCaIE40LBZdamIT1nxev8z3Ck4/1/public/full?alt=json")
  data = r.json()["feed"]["entry"]
  previous_total = int(data[-1][column_name]['$t'])
  if  previous_total == today_data:
    previous_total = int(data[-2][column_name]['$t']) #use previous row if current row equals today (spreadsheet already up to date)
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

  #total tests
  testtotal_table = soup.find(id="testtotal")
  cells = testtotal_table.find_all("td")
  total_tests = int(cells[0].get_text().strip().replace(",",""))

  #new cases
  new_cases = get_daily_change("gsx$totalcases", total_cases)

  #new tests
  new_tests = get_daily_change("gsx$tests-total", total_tests)

  #date and time
  date = datetime.datetime.now().strftime("%-m/%-d/%Y")
  time = datetime.datetime.now().strftime("%-I:%M %p")

  return {"total_cases": total_cases, "new_deaths": new_deaths, "total_tests": total_tests, "new_cases": new_cases, "new_tests": new_tests, "date": date, "time": time}

def scrape_full_test_history():
  pass

@app.route("/spreadsheet")
def spreadsheet_row():
  return render_template("spreadsheet-row.html", data = scrape_spreadsheet_row())

if __name__ == '__main__':
  app.run()
