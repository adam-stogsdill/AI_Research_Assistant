import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import base64
import re
from tqdm import tqdm
import requests
from bs4 import BeautifulSoup

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class Paper:

    def __init__(self, url, arxiv):
        self.url = url
        self.arxiv = arxiv

    def __str__(self):
        return f"Paper:\t{self.url}\n\t\t{self.arxiv}"

paper_list = []


def get_email_body(service, message_id):
    message = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    payload = message['payload']
    headers = payload.get('headers')
    subject = next(header['value'] for header in headers if header['name'] == 'Subject')

    if "Daily papers" not in subject:
        return None

    parts = payload.get('parts')

    body = ""
    if 'data' in payload['body']:
        body = base64.urlsafe_b64decode(payload['body']['data'].encode("ASCII")).decode("utf-8")
    elif parts:
        for part in parts:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                body = base64.urlsafe_b64decode(part['body']['data'].encode("ASCII")).decode("utf-8")
                break
    return body


def investigate_link(url):
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        divs = soup.find_all('div', class_="flex gap-2 py-6 max-sm:flex-col")
        # print(type(divs[0]))
        arxiv_download_link = re.findall('"https:[\/]{2}arxiv.org\/abs\/[0-1a-zA-z\d.?=&-]*"', str(divs[0]))
        #print(arxiv_download_link)
        paper_list.append(Paper(url, arxiv_download_link))

def compile_emails():
    """Shows basic usage of the Gmail API.
        Lists the user's Gmail labels.
        """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        # Call the Gmail API
        service = build("gmail", "v1", credentials=creds)
        results = service.users().messages().list(userId='me', maxResults=30, labelIds=['IMPORTANT']).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No messages found.')
            return

        for message in tqdm(messages):
            body = get_email_body(service, message['id'])
            if body is not None:
                links = re.findall('"https:[\/]{2}huggingface.co\/papers\/[0-1a-zA-z\d.?=&-]*"', body)
                for link in links:
                    investigate_link(link[1:-1])

        for paper in paper_list:
            print(paper)

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f"An error occurred: {error}")

def main():
    # Get the paper list compiled!
    compile_emails()


if __name__ == "__main__":
    main()

#%%
