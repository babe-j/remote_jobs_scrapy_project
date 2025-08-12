import scrapy
from scrapy.http import Request
import json


class RoJobsSpider(scrapy.Spider):
    name = "ro_jobs"
    allowed_domains = ["remoteok.com"]
    start_urls = ["https://remoteok.com/"]

    custom_settings = {
        'FEEDS': {
            'RemoteOK_jobs_items.csv': {
                'format': 'csv',
                'overwrite': True,
                'encoding': 'utf8',
            }
        },

        'DEFAULT_REQUEST_HEADERS': {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en",
            "Accept": "*/*",  # ⚠ This overwrites the first Accept value above
            "Referer": "https://remoteok.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:140.0) Gecko/20100101 Firefox/140.0",
            "X-Requested-With": "XMLHttpRequest",  # Mimics AJAX request headers
        },
    }

    def parse(self, response):
        # Instead of scraping the HTML directly from the homepage,
        # we jump straight to a specific endpoint that delivers job data
        # in a JSON-friendly format. "offset=1" means first page of job listings.
        url = "https://remoteok.com/?&action=get_jobs&offset=1"
        yield Request(
            url=url,
            callback=self.parse_jobs,       # Send this request’s result to parse_jobs()
            meta={'dont_redirect': True}    # Prevents Scrapy from following HTTP redirects automatically
        )

    def parse_jobs(self, response):
        jobs = []
        if response.status == 200:
            try:
                # Extract JSON-LD blocks from <script type="application/ld+json">
                # JSON-LD is structured data embedded in HTML for SEO and rich results.
                json_scripts = response.css('script[type="application/ld+json"]::text').getall()

                for json_str in json_scripts:
                    try:
                        # Convert raw JSON string into Python dict
                        json_data = json.loads(json_str)
                        jobs.append(json_data)
                    except json.JSONDecodeError as e:
                        # If any script block has malformed JSON, skip it but log a warning
                        self.logger.warning(f"Failed to decode JSON: {e}")

                # If we didn't find *any* job data, stop here for this page
                if len(jobs) == 0:
                    self.logger.info(f"No jobs found on page: {response.url}")
                    return None

            except Exception as e:
                # Catch any unexpected exception in the extraction loop
                self.logger.exception(f"Error message : {e}")

        if jobs:
            for job in jobs:
                # Pull values from JSON safely using .get() to avoid KeyErrors.
                # For nested objects, supply a default {} so .get() can still work.
                job_name = job.get('title', '')
                job_type = job.get('employmentType', '')
                job_url = job.get('hiringOrganization', {}).get('url', '')
                company_name = job.get('hiringOrganization', {}).get('name', '')

                # jobLocation is a list; take index 0 if available, else default to ''
                company_country = job.get('jobLocation', [])[0].get('address', {}).get('addressCountry', '') if job.get('jobLocation') else ''

                date_posted = job.get('datePosted', '')

                # applicantLocationRequirements is also a list; same safety logic
                location_requirements = job.get('applicantLocationRequirements', [])[0].get('name', '') if job.get('applicantLocationRequirements') else ''

                yield {
                    "JOB_NAME": job_name,
                    "JOB_TYPE": job_type,
                    "JOB_URL": job_url,
                    "COMPANY_NAME": company_name,
                    "COMPANY_COUNTRY": company_country,
                    "DATE_POSTED": date_posted,
                    "LOCATION_REQUIREMENTS": location_requirements
                }

        try:
            # Figure out which page we’re currently on from the "offset" query parameter.
            # Example: "...offset=3" → current_page = 3
            current_page = int(response.url.split('=')[-1])

            # Calculate next page number
            next_page = current_page + 1

            # Build the URL for the next page of jobs
            base_url = "https://remoteok.com/?&action=get_jobs&offset={}"
            next_page_url = base_url.format(next_page)

            # Recursively follow to next page until no more jobs found
            yield response.follow(
                url=next_page_url,
                callback=self.parse_jobs,
                meta={'dont_redirect': True}
            )

        except Exception as e:
            # If URL format changes or offset parsing fails, stop pagination for safety
            self.logger.warning(f"Pagination failed: {e}")
