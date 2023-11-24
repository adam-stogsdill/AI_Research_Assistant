import customtkinter
import os
from PIL import Image
import pickle

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
import tkinter as tk

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class ScrollingTimeTabs(customtkinter.CTkScrollableFrame):

    def __init__(self, master, command=None, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.command = command
        self.radiobutton_variable = customtkinter.StringVar()
        self.label_list = []
        self.button_list = []

    def add_item(self, item, text="NULL", dict_of_papers=""):
        confirm_button = customtkinter.CTkButton(self, text=text, width=100, height=24)
        if self.command is not None:
            confirm_button.configure(command=lambda: self.command(item, dict_of_papers))
        confirm_button.grid(row=len(self.button_list), column=0, pady=(0, 10), padx=5)
        self.button_list.append(confirm_button)

    def remove_item(self, item):
        for label, button in zip(self.label_list, self.button_list):
            if item == label.cget("text"):
                label.destroy()
                button.destroy()
                self.label_list.remove(label)
                self.button_list.remove(button)

    def __del__(self):
        for label, button in zip(self.label_list, self.button_list):
            label.destroy()
            button.destroy()
            self.label_list.remove(label)
            self.button_list.remove(button)


class ScrollingPaperInfoFrame(customtkinter.CTkScrollableFrame):

    def __init__(self, master, command=None, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)

        self.command = command
        self.radiobutton_variable = customtkinter.StringVar()
        self.label_list = []
        self.button_list = []
        self.sublabel_list = []

    def add_item(self, item, paper_obj=None, image=None):
        label = customtkinter.CTkLabel(self, text=item, image=image, padx=5, anchor="w", width=100)
        sub = customtkinter.CTkLabel(self, text="Nothing here RN", image=image, padx=5, anchor="w", width=100)
        confirm_button = customtkinter.CTkButton(self, text="CONFIRM", width=100, height=24)
        if self.command is not None:
            confirm_button.configure(command=lambda: self.command(paper_obj))
        label.grid(row=len(self.label_list), column=0, pady=(0, 10), sticky="w")
        sub.grid(row=len(self.sublabel_list), column=1, pady=(0, 10), sticky="w")
        confirm_button.grid(row=len(self.button_list), column=2, pady=(0, 10), padx=5)
        self.label_list.append(label)
        self.sublabel_list.append(sub)
        self.button_list.append(confirm_button)

    def remove_item(self, item):
        for label, button in zip(self.label_list, self.button_list):
            if item == label.cget("text"):
                label.destroy()
                button.destroy()
                self.label_list.remove(label)
                self.button_list.remove(button)

    def __del__(self):
        for label, button in zip(self.label_list, self.button_list):
            label.destroy()
            button.destroy()
            self.label_list.remove(label)
            self.button_list.remove(button)


class Paper:

    def __init__(self, url, arxiv, title):
        self.url = url
        self.arxiv = arxiv
        self.title = title

    def __str__(self):
        return f"Paper:\t{self.title}\n\t\t{self.url}\n\t\t{self.arxiv}"


def get_email_body(service, message_id):
    message = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    payload = message['payload']
    headers = payload.get('headers')
    subject = next(header['value'] for header in headers if header['name'] == 'Subject')

    if "Daily papers" not in subject:
        return None, None

    parts = payload.get('parts')

    body = ""
    if 'data' in payload['body']:
        body = base64.urlsafe_b64decode(payload['body']['data'].encode("ASCII")).decode("utf-8")
    elif parts:
        for part in parts:
            if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                body = base64.urlsafe_b64decode(part['body']['data'].encode("ASCII")).decode("utf-8")
                break
    return subject, body


def investigate_link(url):
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        h1 = soup.find_all('h1',
                           class_='mb-2 text-2xl font-semibold sm:text-3xl lg:pr-6 lg:text-3xl xl:pr-10 2xl:text-4xl')

        title = re.findall('>[\W\w]*<', str(h1[0]))
        #print(str(h1[0]), title)

        divs = soup.find_all('div', class_="flex gap-2 py-6 max-sm:flex-col")
        # print(type(divs[0]))
        arxiv_download_link = re.findall('"https:[\/]{2}arxiv.org\/abs\/[0-1a-zA-z\d.?=&-]*"', str(divs[0]))
        # print(arxiv_download_link
        return Paper(url, arxiv_download_link[0][1:-1], title[0][1:-1].replace("\n  ", " "))


def compile_emails():
    """Shows basic usage of the Gmail API.
        Lists the user's Gmail labels.
        """

    dict_of_papers = {}

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
            subject, body = get_email_body(service, message['id'])
            dict_of_papers[subject] = []
            if body is not None:
                links = re.findall('"https:[\/]{2}huggingface.co\/papers\/[0-1a-zA-z\d.?=&-]*"', body)
                for link in links:
                    paper_obj = investigate_link(link[1:-1])
                    #print(paper_obj)
                    dict_of_papers[subject].append(paper_obj)

        return dict_of_papers

    except HttpError as error:
        print(f"An error occurred: {error}")


class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("AI Paper Program")
        self.geometry("2000x500")

        displayed_keys = []

        dict_of_papers = None
        with open("./example_dict.pkl", 'rb') as f:
            dict_of_papers = pickle.load(f)

        '''dict_of_papers = compile_emails()
        with open("./example_dict.pkl", 'wb') as f:
            pickle.dump(dict_of_papers, f)'''

        self.grid_rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # create scrollable checkbox frame
        self.scrollable_time_tabs = ScrollingTimeTabs(master=self, width=200,
                                                      command=self.label_button_frame_event)
        self.scrollable_time_tabs.grid(row=0, column=0, padx=0, pady=0, sticky="ns")
        for paper_subject in dict_of_papers:
            if paper_subject is not None:
                print(dict_of_papers[paper_subject][0])
                displayed_keys.append(paper_subject)
                self.scrollable_time_tabs.add_item(paper_subject, paper_subject, dict_of_papers)

        # create scrollable label and button frame
        self.scrollable_label_button_frame = ScrollingPaperInfoFrame(master=self, width=300,
                                                                     command=self.checkbox_frame_event)
        self.scrollable_label_button_frame.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")
        for paper in dict_of_papers[displayed_keys[0]]:  # add items with images
            print(paper.title)
            self.scrollable_label_button_frame.add_item(f"{paper.title}",
                                                        paper_obj=paper,
                                                        image=None)


    def checkbox_frame_event(self, paper_obj):
        print(paper_obj)

    def label_button_frame_event(self, item, dict_of_papers):
        print(dict_of_papers)
        print(f"label button frame clicked: {item}")
        for idx in range(len(self.scrollable_label_button_frame.button_list) - 1, -1, -1):
            # print(checkbox_idx)
            self.scrollable_label_button_frame.button_list[idx].destroy()
            del self.scrollable_label_button_frame.button_list[idx]
            self.scrollable_label_button_frame.label_list[idx].destroy()
            del self.scrollable_label_button_frame.label_list[idx]
            self.scrollable_label_button_frame.sublabel_list[idx].destroy()
            del self.scrollable_label_button_frame.sublabel_list[idx]


        for paper in dict_of_papers[item]:  # add items with images
            print(paper.title)
            self.scrollable_label_button_frame.add_item(f"{paper.title}",
                                                        paper_obj=paper,
                                                        image=None)


if __name__ == "__main__":
    customtkinter.set_appearance_mode("dark")
    app = App()
    app.mainloop()
