# Smart-California-Business-Finder
A high-performance Python scraper using Playwright and AI to extract verified leads (Emails, Phones, Addresses) from Google Maps and official websites.

## The lead_scraper/maps_scraper.py module handles the core extraction logic using Playwright:

1- Targeted Search: Automates searches for "Churches in California" and "Hospitals in California" on Google Maps.
2- Result Navigation: Performs automated scrolling to discover and collect direct links for all location results.
3- Data Extraction: Scrapes the Name, Phone, Address, and Website for each identified organization.
4- Location Parsing: Intelligently extracts the City and State directly from the full address strings.
5- Data Validation: Automatically filters and removes any records that are missing mandatory Email or Phone details to ensure lead quality.