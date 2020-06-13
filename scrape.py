import sys
import time
import utils

from os import path
from datetime import datetime
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.support import expected_conditions as EC

blacklisted_tags = ["noise", "noisegrind", "harsh.noise"]
cutoff_year = 2019

def get_download_link(driver):
    driver.find_element_by_class_name("download-link.buy-link").click()
    driver.find_element_by_id("userPrice").send_keys("0")
    driver.find_element_by_link_text("download to your computer").click()
    try:
        driver.find_element_by_xpath("//div[@id='downloadButtons_download']/div[1]/button[1]").click()
    except ElementNotInteractableException:
        return False
    driver.find_element_by_class_name("item-format.button").click()
    try:
        driver.find_element_by_xpath("//span[@class='description selected' and text()='FLAC']/..")
    except NoSuchElementException:
        driver.find_element_by_xpath("//span[@class='description' and text()='FLAC']/..").click()
    element = WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.LINK_TEXT, "Download"))
    )
    return element.get_attribute("href")

def main():
    release_ct = int(input("Number of Releases: "))

    cache = utils.read_file("./cache.txt")
    if cache:
        cache = cache.split("\n")
    else:
        cache = []

    #Load Bandcamp
    driver = webdriver.Firefox()
    driver.get("https://bandcamp.com")
    driver.implicitly_wait(2)

    #Get New/Digital Releases
    driver.find_element_by_class_name("discover-pill.new").click()
    driver.find_element_by_class_name("discover-pill.digital").click()

    #Wait for Page
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//a[@class='item-page' and text()='next']")))

    releases = []

    while len(releases) < release_ct:
        #Get Releases
        albums = driver.find_elements_by_xpath("//div[contains(@class, 'row discover-result') and contains(@class, 'result-current')]/div[@class='col col-3-12 discover-item']/a[2]")
        for album in albums:
            if len(releases) >= release_ct:
                break

            #Parse URL
            parsed_url = urlparse(album.get_attribute("href"))
            url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path

            #Check Cache
            if url in cache:
                continue
            cache.append(url)

            #Open New Tab
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[1])
            driver.get(url)

            #Check if Releases Matches Filters
            try:
                price_element = driver.find_element_by_class_name("buyItemExtra.buyItemNyp.secondaryText")
                year_element = driver.find_element_by_xpath("//meta[@itemprop='datePublished']")
                tag_element = driver.find_elements_by_xpath("//a[@class='tag']")

                #Get Release Year
                year = int(datetime.strptime(year_element.get_attribute("content"), "%Y%m%d").year)

                #Check Tags
                blacklisted = False
                for tag in tag_element:
                    if tag.text in blacklisted_tags:
                        blacklisted = True
                        break

                #Check Price and Release Year
                if price_element.text == "name your price" and year >= cutoff_year and not blacklisted:
                    download_link = get_download_link(driver)
                    if download_link:
                        releases.append(f"{url}, {download_link}")
            except NoSuchElementException:
                pass
            
            #Close New Tab
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        else:
            #Load Next Page of Releases
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//a[@class='item-page' and text()='next']"))).click()

    driver.close()

    utils.write_file("./releases.txt", "\n".join(releases))
    utils.write_file("./cache.txt", "\n".join(cache))

if __name__ == "__main__":
    main()