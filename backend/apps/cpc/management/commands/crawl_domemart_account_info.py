from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '도매마트(domemart.co.kr) 예치금+주문상태 현황 수집'

    def handle(self, *args, **options):
        from crawlers.domemart_crawler import new_driver, crawl_account_info

        driver = new_driver(user_data_dir='/tmp/domemart_info_profile')
        try:
            result = crawl_account_info(driver, log_fn=lambda m: self.stdout.write(m))
        finally:
            driver.quit()
        self.stdout.write(self.style.SUCCESS(str(result)))
