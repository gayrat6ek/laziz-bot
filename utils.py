import gspread
from google.oauth2.service_account import Credentials

# Google Sheets setup



def send_to_sheet(name,phone,score,username):
    SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"  # required to search by title
    ]
    CREDS = Credentials.from_service_account_file("abulaziz-7b85d06b6813.json", scopes=SCOPES)
    client = gspread.authorize(CREDS)
    sheet = client.open("Urolog").worksheet("Sheet1")


    sheet.append_row([name,phone,score,username])
    return True

