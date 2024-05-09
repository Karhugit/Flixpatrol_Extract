import requests
import os.path
import time
from bs4 import BeautifulSoup
import sys
from fuzzywuzzy import fuzz
import re
trace = False
headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_17) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36'}

client_id = '378e7c8adf3569e809b57a26e318dee3d4080e3c58dafa817537f6b7d6662cd6'
client_secret = 'e454afd65b734faea58be818af256bb05e88e6151404df987d5716025dbc0b29'
auth_base_url = 'https://api.trakt.tv/oauth/device/code'
token_file = 'trakt_token.txt'
trakt_base_url = 'https://api.trakt.tv/users/me/'
trakt_token_url = 'https://api.trakt.tv/oauth/device/token'
trakt_list_url = 'https://api.trakt.tv/users/karhu69/lists/Netflix-Top10-Movies/items/'
trakt_list_url_template = 'https://api.trakt.tv/users/me/lists/Netflix-Top10-xxxxxx/items/'
trakt_list_remove_url = 'https://api.trakt.tv/users/me/lists/Netflix-Top10-Movies/items/remove'
trakt_list_add_url = 'https://api.trakt.tv/users/karhu69/lists/Netflix-Top10-Movies/items'
trakt_search_movies_url = 'https://api.trakt.tv/search/movie?query='
movies_list = []
tvshows_list = []

def get_trakt_me(test_token):
    trakt_headers = {'content-type': 'application/json','authorization': test_token,'trakt-api-version': '2','trakt-api-key': client_id}
    if trace:
        print(trakt_headers)
    response = requests.get('https://api.trakt.tv/users/me',headers=trakt_headers)
    if response.status_code == 200:
        # Token works, lets go!
        return True
    else:
        # Token failed
        return response.status_code

def get_trakt_code():
    trakt_headers = {'Content-Type': 'application/json','trakt-api-key': client_id}
    trakt_payload = {'client_id': client_id}
    response = requests.post(auth_base_url,json=trakt_payload,headers=trakt_headers)
    if trace:
        print('header ',trakt_headers,' payload ',trakt_payload)
    if response.status_code == 200:
        if trace:
            print('Good response received from trakt')
        data = response.json()
        device_code = data['device_code']
        user_code = data['user_code']
        if trace:
            print("user code is ",user_code)
        verification_url = data['verification_url']
        if trace:
            print('Verification URL is ',verification_url)
        return [user_code, device_code]
    else:
        return None

def get_trakt_oauth(device_cde):
        trakt_headers = {'Content-Type': 'application/json','trakt-api-key': client_id,'trakt-api-version': '2'}
        trakt_payload = {'code': device_cde,'client_id': client_id,'client_secret': client_secret}
        if trace:
            print('header ',trakt_headers,' payload ',trakt_payload)
        poll_interval = 5
        tries_limit = 40
        tries = 0
        while tries < tries_limit:
            response = requests.post(trakt_token_url,json=trakt_payload,headers=trakt_headers)
            if trace:
                print('trakt response code ',response.status_code)
            tries = tries + 1
            if trace:
                print('tries =',tries)
            if response.status_code == 200:
                if trace:
                    print('Got the access token!!')
                data = response.json()
                access_token = ('Bearer ' + data['access_token'])
#                access_token = data['refresh_token']
                if trace:
                    print('access token =', access_token)
                return(access_token)
            elif response.status_code == 400:
                if trace:
                    print('Still waiting for trakt auth')
                time.sleep(poll_interval)
            else:
                print('Failed to authenticate with trakt')
                break

def find_good_access_token():
    #If we are lucky, there is a good one in the file
    #Is there a file?
    try:
        with open(token_file,'r') as f:
            file_token = f.read().strip()
            open(token_file).close()
            # Found a token file with a record
            # Lets test it before we return it
            if file_token:
                if get_trakt_me(file_token):
                    # Token works
                    if trace:
                        print('Found working token : ',file_token)
                    return (file_token)
                else:
                    if trace:
                        print('Found token in file, does not auth')
                    # Empty the file
                    open(token_file,'w').close()
            else:
                if trace:
                    print('File exists but no token')
    except FileNotFoundError:
# No file found, can we create one?
        f = open(token_file,'a')
        if f:
            if trace:
                print('Created token file')
        else:
            if trace:
                print('Could not create token file')
# If we got here, either no token or file found. Lets get a token
# Even if we can't put it into the file we could use it one time
    auth_code, device_code = get_trakt_code()
    if auth_code:
        print ('Please activate trakt device using : ',auth_code)
        access_token = get_trakt_oauth(device_code)
        if trace:
            print('Got access token',access_token)
        f = open(token_file,'w')
        if f:
            # if we have an open file, write the access token to it
            f.write(access_token)
            open(token_file).close()
        return (access_token)
    else:
        print('Unable to get auth code for trakt authorisation')
        return 'No token'
    


def get_flixpatrol_top10():
    res = requests.get("https://flixpatrol.com/top10/netflix/united-states/",headers = headers)
    soup = BeautifulSoup(res.text,'html.parser')
    # Find the first tabular-nums class, which is movies
    txt_data = soup.body.find('tbody',class_ = 'tabular-nums')
    tvshow_data = soup.body.find_next('tbody',class_ = 'tabular-nums')

    # Find the table
    # Find the first group
    tr = txt_data.find_all('tr')
    for item in tr:
        tr_item = item.find_all('td')
        for item2 in tr_item:
            if len(item2['class']) == 1:
                if item2['class'] == ['table-td']:
                    if trace:
                        print('Found our titles ',item2)
                    for item3 in item2:
                        extracted_text = re.findall(r'>(.*?)<',str(item3))
                        if extracted_text:
                            if len(extracted_text) ==1:
                                movies_list.append(extracted_text)

    # Find Tv shows
    tr = tvshow_data.find_all('tr')
    for item in tr:
        tr_item = item.find_all('td')
        for item2 in tr_item:
            if len(item2['class']) == 1:
                if item2['class'] == ['table-td']:
                    if trace:
                        print('Found our titles ',item2)
                    for item3 in item2:
                        extracted_text = re.findall(r'>(.*?)<',str(item3))
                        if extracted_text:
                            if len(extracted_text) ==1:
                                tvshows_list.append(extracted_text)

    print('Tvshows extracted - ',tvshows_list)

    if trace:
        print('extracted : ',movies_list)
    return True

def make_movie_payload(trakt_id_list):
    movie_payload = {'movies':[]}
    item_list = []
    idividual_item = {}
    for index,item in enumerate(trakt_id_list):
        individual_item = {'ids':{'trakt':item}}
        movie_payload['movies'].append(individual_item)
    return movie_payload

def process_list(type):
    if trace:
        print('List type = ',type)
    # Is there already a netflix list?
    trakt_headers = {'content-type': 'application/json','authorization': token_result,'trakt-api-version': '2','trakt-api-key': client_id}
    if trace:
        print(trakt_headers)
    list_url = trakt_list_url_template.replace('xxxxxx',str(type))

    response = requests.get(list_url,headers=trakt_headers)
    if trace:
        print('Get list response code : ',response.status_code)
    if response.status_code == 200:
        data = response.json()
    else:
        # No list, so create one
        #Create new trakt list
        Dname = 'Netflix-Top10-' + str(type)
        Desc = 'Netflix Top 10 ' + str(type) + ' in the US, updated daily'
        trakt_payload = {'name': Dname,
                         'description': Desc,
                         'privacy': 'public',
                         'display_numbers': True,
                         'allow_comments': True,
                         'sort_by': 'rank',
                         'sort_how': 'asc'}
        list_url = trakt_base_url + 'lists/'
        response = requests.post(list_url,json=trakt_payload,headers=trakt_headers)
        if trace:
            print('trakt response code ',response.status_code)
        # If we can't create the new list, bail out here
        if response.status_code != 201:
            print('Unable to create new trakt list, bailing out')
            sys.exit()
        else:
        # New list created, no need to delete any items
            return True    
    #OK, new list created, now to populate the items for the list
    # Found the list so build a list of items and delete from the list
    item_del_list = []
    for item in data:
        itemd = dict(item)
        test = dict(itemd['movie'])
        ids = dict(test['ids'])
        if trace:
            print('trakt id = ',ids['trakt'])
        trakt_id = ids['trakt']
        trakt_id_str = str(trakt_id)
        if trace:
            print('trakt id is ',trakt_id_str)
        item_del_list.append(trakt_id)
    if trace:
        print('items to be deleted = ',item_del_list)
    trakt_payload = {}
    trakt_payload = make_movie_payload(item_del_list)
    if trace:
        print('Make payload says yes',trakt_payload)
    # Got the list, build the payload and delete the items
    if trace:
        print(trakt_payload)
 #   trakt_payload = {trakt_payload_strd}
    trakt_headers = {'content-type': 'application/json','authorization': token_result,'trakt-api-version': '2','trakt-api-key': client_id}
    response = requests.post(trakt_list_remove_url,json=trakt_payload,headers=trakt_headers)
    if trace:
        print('trakt response code ',response.status_code)
    data = response.json
    if trace:
        print('data in resp is',data)
    return True

#first we need to get a valid access token for trakt, if we have/get one it will be in the token file
token_result = find_good_access_token()
if token_result == "No token":
    print('No valid trakt token found or created, bailing here')
else:
    if trace:
        print('Good access token found ',token_result)

#Handle netflix top10 movies
extracted = get_flixpatrol_top10()
if extracted:
    if trace:
        print(movies_list)
    if not process_list('Movies'):
        print('Unable to create the trakt list - bailing here')
        sys.exit()

    if not process_list('TVShows'):
        print('Unable to create the trakt list - bailing here')
        sys.exit()

    # Movies_list contains the list of the titles
    movie_object = {'movies':{}}
    # Lets build the payload the hard way
    trakt_id_list = []
    trakt_headers = {'content-type': 'application/json','authorization': token_result,'trakt-api-version': '2','trakt-api-key': client_id}
    for item in movies_list:
        stripped_title = ""
        stripped_title = str(item)
        stripped_title = stripped_title.replace('[','')
        stripped_title = stripped_title.replace(']','')
        stripped_title = stripped_title.lstrip("'")
        stripped_title = stripped_title.rstrip("'")


        if trace:
            print('stripped title :',stripped_title)
        # Search trakt for the movie
        movie_search_url = trakt_search_movies_url + stripped_title + '&fields=title&extended=full'
        if trace:
            print(movie_search_url)
        response = requests.get(movie_search_url,headers=trakt_headers)
        if trace:
            print(response.status_code)
        data = response.json()
        for item in data:
            itemd = dict(item)
            if trace:
                print(itemd['movie'])
            movie_deets = dict(itemd['movie'])
            if trace:
                print('comparing',stripped_title,movie_deets['title'])
            similarity_score = fuzz.ratio(stripped_title,movie_deets['title'])
            votes = movie_deets['votes']
            if trace:
                print('similarity = ',similarity_score)
            if similarity_score > 89:
                if votes > 29:
                    if trace:
                        print(movie_deets['ids'])
                        print(movie_object['movies'])
                    ids = movie_deets['ids']
                    idsd = dict(ids)
                    trakt_id = idsd['trakt']
                    trakt_id_str = str(trakt_id)
                    if trace:
                        print('trakt id is ',trakt_id_str)
                    trakt_id_list.append(trakt_id)
                    if trace:
                        print('trakt id list is ',trakt_id_list)
                    break

    trakt_payload = {}
    trakt_payload = make_movie_payload(trakt_id_list)
    if trace:
        print('Make payload says yes',trakt_payload)
    # Got the list, build the payload and delete the items
    if trace:
        print(trakt_payload)
    if trace:
        print(trakt_payload)
    trakt_headers = {'content-type': 'application/json','authorization': token_result,'trakt-api-version': '2','trakt-api-key': client_id}
    if trace:
        print(trakt_payload)
    response = requests.post(trakt_list_add_url,json=trakt_payload,headers=trakt_headers)
    if trace:
        print('trakt response code ',response.status_code)
    data = response.json

    
