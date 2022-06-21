#!/usr/bin/env python
from io import StringIO
import smtplib
import ssl
import csv
import threading
import requests
import os
import schedule 
import time

def request(resource,*args):

	retry = True
	while retry:

		try:
			if resource == "csv":
				url = "http://fs.smartctl.cl/*************.csv"
				r = requests.get(url,headers={"User-Agent": "Mozilla Firefox" })
				retry = False
				return r

			if resource == "zoho":
				url = "https://inventory.zoho.com/api/v1/items?organization_id={}&authtoken={}&page={}"
				r = requests.get(url.format(args[0],args[1],args[2]))
				retry = False
				return r

			if resource == "NoP":
				url = "https://api.jumpseller.com/v1/products/count.json?login=*****************************&authtoken=**************************"
				r = requests.get(url)
				retry = False
				return r

			if resource == "products":
				url = "https://api.jumpseller.com/v1/products.json?login=*****************************&authtoken=**************************&limit={}&page={}"
				r = requests.get(url.format(args[0],args[1]))
				retry = False
				return r

			if resource == "update":
				headers={"Content-Type": "application/json" }
				url = "https://api.jumpseller.com/v1/products/{}.json?login=*****************************&authtoken=**************************"
				r = requests.put(url.format(args[0]), data='{"product": { "stock": "'+str(args[1])+'"} }',headers=headers)
				retry = False
				return r

		except:
			print("Connection error, retrying...")
			continue


def update_quantity():

	# Download provider csv
	print("Downloading CSV")
	
	response = request("csv")
	#########ZOHO#############

	authtoken = "****************************"
	organization_id = "*********"

	# zoho_items_url = "https://inventory.zoho.com/api/v1/items?organization_id={}&authtoken={}&page={}"

	zoho_items = []
	page = 1

	print("Requesting ZOHO items")
	while True:
		items_res = request("zoho",organization_id,authtoken,page)

		zoho_items += items_res.json()['items']
		page += 1

		if not items_res.json()['page_context']['has_more_page']:
			break

	print("Ordering ZOHO items")
	item_filter = []

	for item in zoho_items:
		if len(item['part_number']) > 0:
			item_filter.append(item) 


	######## JUMP SELLER #########

	print("Requesting number of products JUMPSELLER")
	# Query number of products
	number_of_products_json = request("NoP")

	# Calculate all products for loop
	total = number_of_products_json.json()['count']
	cent = int(total/100)
	rest = total-(cent*100)

	# Url to query all the products in the store 
	products = []
	
	print("Requesting all JUMPSELLER products")
	# Loops for pagination
	for i in range(1,cent+1):
		product_res = request("products",100,i)
		products += product_res.json()

	if rest > 0:
		product_res = request("products",rest,cent+1)
		products += product_res.json()

	not_updated_products = []
	to_update_products = {}

	############# FINAL PROCESS ##############

	print("Updating coincidences")
	c = 0
	for product in products:
		print(c + 1)
		lower_product = ''.join(e for e in str(product['product']['sku']).lower() if e.isalnum())
		id_product = product['product']['id']
		prov = csv.reader(StringIO(response.text), delimiter=',')
		headers = prov.__next__()
		c1 = 0
		for item in item_filter:
			lower_item = ''.join(e for e in str(item['part_number']).lower() if e.isalnum())
			try:
				if lower_product == lower_item:
					to_update_products[lower_product] = [id_product,int(item['stock_on_hand'])]
					del item_filter[c1]
			except:
				pass
			c1 += 1

		for row in prov:
			lower_row = ''.join(e for e in str(row[3]).lower() if e.isalnum())
			if lower_product == lower_row:
				if not_updated_products.count(lower_product) != 0:
					not_updated_products.remove(lower_product)
				if lower_product in to_update_products:
					to_update_products[lower_product][1] += int(row[16])
				else:
					to_update_products[lower_product] = [id_product,int(row[16])]

		if len(to_update_products) > 0:
			if lower_product !=list(to_update_products)[-1]:
				not_updated_products.append(product['product']['sku'])

	print("Sending updates")
	url_update= "https://api.jumpseller.com/v1/products/{}.json?login=*****************************&authtoken=**************************"
	headers={"Content-Type": "application/json" }
	for sku in to_update_products:

		############# LINEA QUE ACTUALIZA #################
		r = request("update",to_update_products[sku][0],to_update_products[sku][1])
		print(sku+" -- updated")

	sender = '************'
	receivers = ['****************']

	message = "From: No Reply <************>\r\nTo: A <rurdanta@smartctl.co>\r\nSubject: Log de productos que no se actualizaron\r\n\r\n{}".format(" ".join(not_updated_products))

	context = ssl.create_default_context()

	with smtplib.SMTP_SSL('**********', port=465, context=context) as server:
		server.login('************', '**********')
		server.sendmail(sender, receivers, message)         
		print("Successfully sent email")

	print("Done!")

if __name__ == "__main__":

	########## DESCOMENTA ESTO Y EJECUTA SI QUIERES ACTUALIZAR MANUALMENTE
	update_quantity()

	# schedule.every().day.at("06:00").do(update_quantity)
	# while True:
	# 	schedule.run_pending() 
	# 	time.sleep(1)

