from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '도매마트 주문/배송조회(최근 1개월) 송장정보(받는분휴대폰/배송사/송장번호) 다운로드'

    def handle(self, *args, **options):
        from crawlers.domemart_crawler import new_driver, crawl_invoice_download

        driver = new_driver(user_data_dir='/tmp/domemart_invoice_profile')
        try:
            result = crawl_invoice_download(
                driver, '/tmp/avengers_domemart_invoice_dl', log_fn=lambda m: self.stdout.write(m))
        finally:
            driver.quit()
        if result.get('ok'):
            self.stdout.write(self.style.SUCCESS(str(result)))
        else:
            self.stderr.write(str(result))
