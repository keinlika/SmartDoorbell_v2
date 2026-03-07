import os

import requests

from supabase import create_client

from dotenv import load_dotenv



# 1. Load Secrets

load_dotenv()



url = os.environ.get("SUPABASE_URL")

key = os.environ.get("SUPABASE_KEY")

supabase = create_client(url, key)



# --- USER CREDENTIALS ---

USER_EMAIL = "lik19001@byui.edu"  

USER_PASSWORD = "ShokuPal1998!"        



def run_test():

    print(f"1. Attempting to log in as {USER_EMAIL}...")

    

    try:

        # A. Log in to Supabase Auth

        session = supabase.auth.sign_in_with_password({

            "email": USER_EMAIL, 

            "password": USER_PASSWORD

        })

        

        # B. Extract the 'Key' (Access Token)

        access_token = session.session.access_token

        print("   SUCCESS! Token received.")

        print(f"   Token snippet: {access_token[:20]}...")



        # C. Use the Key to open the API Door

        print("\n2. Connecting to Local API...")

        api_url = "http://localhost:8000/devices"

        

        # This is the magic header that unlocks the door

        headers = {

            "Authorization": f"Bearer {access_token}"

        }

        

        response = requests.get(api_url, headers=headers)

        

        # D. Show Results

        if response.status_code == 200:

            print("\n   ACCESS GRANTED! Here is your data:")

            print(response.json())

        else:

            print(f"\n   ACCESS DENIED. Status: {response.status_code}")

            print(response.text)



    except Exception as e:

        print(f"\n   ERROR: {e}")



if __name__ == "__main__":

    run_test()
