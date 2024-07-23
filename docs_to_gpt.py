from bs4 import BeautifulSoup 
import requests 
from urllib.parse import urljoin
import json
import tiktoken

# lists 
urls=[]

def get_docs(url: str):
	r = requests.get("https://r.jina.ai/" + url)
	return r.text

dic = {}
page_count = 0
total_tokens = 0

# function created 
def scrape(site): 
	global page_count, total_tokens
	
	# getting the request from url 
	r = requests.get(site)
	
	# converting the text 
	s = BeautifulSoup(r.text, "html.parser") 
	for i in s.find_all("a"): 
		href = i.attrs.get('href')  # use get to avoid KeyError if 'href' is missing
		if href:
			# construct the full URL
			full_url = urljoin(site, href)
			cleaned_url = full_url.split('#')[0]

			# normalize the URL to avoid duplicates
			if cleaned_url not in urls and "https://docs.chainlit.io" in full_url: 
				urls.append(cleaned_url)
				print(cleaned_url)
				if dic.get(cleaned_url) is None:
					text = get_docs(cleaned_url)
					dic[cleaned_url] = text
					page_count += 1

					# Calculate tokens using tiktoken
					encoding = tiktoken.encoding_for_model("gpt-4")
					tokens_url = len(encoding.encode(cleaned_url))
					tokens_text = len(encoding.encode(text))
					total_tokens += tokens_url + tokens_text
				
				# calling itself to scrape the next page
				scrape(cleaned_url)

# main function 
if __name__ == "__main__": 

	# website to be scraped 
	site = "https://python.langchain.com/v0.2/docs/introduction"
	output_file_name = "langchain_docs.json"
	# calling function 
	scrape(site)
	with open(output_file_name, "w") as f:
		json.dump(dic, f, indent=4)
	
	print(f"Total pages scraped: {page_count}")
	print(f"Total tokens scraped: {total_tokens}")
