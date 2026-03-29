# ImmigrationInterviewsUSA

A data driven tool that helps estimate when U.S. immigration interviews may occur by transforming visa bulletin data into realistic timelines.

## Overview

Immigration timelines are often unclear. While the U.S. Department of State publishes visa bulletin data, it is not designed for practical forecasting.

ImmigrationInterviewsUSA bridges that gap.

This tool analyzes historical visa bulletin movement and combines it with consulate level scheduling patterns to estimate:

* When a case may become current
* Expected interview scheduling windows
* Consulate specific timing differences

## Why this exists

This project is personal.

After going through the immigration process myself, I experienced the uncertainty of waiting and trying to predict when my spouse’s interview would happen. The data exists, but it is fragmented and difficult to interpret.

This tool was built to turn that uncertainty into something more actionable.

## Features

* Visa bulletin ingestion and parsing from travel.state.gov
* Forecasting based on historical cutoff movement
* Confidence based projection windows
* Consulate specific scheduling insights
* IR and CR forecasting based on real consulate wait times
* Interactive dashboard built with Streamlit
* Dark, product focused UI for clarity and usability

## How it works

### Non IR categories (Family and Employment)

* Tracks monthly cutoff date progression
* Calculates average movement and variance
* Projects when a priority date becomes current
* Estimates interview timing with an additional scheduling buffer

### IR and CR categories

* No visa bulletin dependency since these are always current
* Forecast is based on:

  * I 130 processing range
  * NVC completion window
  * Consulate specific scheduling wait times

This makes interview estimates location aware instead of generic.

## Tech Stack

* Python
* Streamlit
* Pandas
* NumPy
* Plotly
* BeautifulSoup

## Live App

https://immigrationinterviewsusa.streamlit.app/

## Installation

Clone the repository:

```bash
git clone https://github.com/roxannehernan/immigrationinterviewsusa.git
cd immigrationinterviewsusa
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

## Data Source

Visa bulletin data is sourced from:

https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin.html

## Disclaimer

This tool provides statistical estimates based on historical data and observed patterns.

It is not legal advice and should not be used as a substitute for official guidance or consultation with an immigration attorney.

## Feedback

If you are navigating immigration or working in this space, feedback is welcome.

GitHub: https://github.com/roxannehernan
