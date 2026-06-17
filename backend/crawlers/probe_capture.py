"""SPA의 login-seller 응답을 후킹 캡처해 진짜 sellerNo 확보 검증"""
import os, sys, time, re, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from crawlers.browser import create_driver, stop_display
from crawlers import eleven_crawler as _ec
from apps.cpc.models import CrawlerAccount

LID = sys.argv[1] if len(sys.argv) > 1 else 'dlrmsgh011'

HOOK = r"""
(function(){
  window.__sellerNo = null;
  try {
    var oo = XMLHttpRequest.prototype.open, os_ = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(m,u){ this.__u=u; return oo.apply(this,arguments); };
    XMLHttpRequest.prototype.send = function(){
      var self=this;
      this.addEventListener('load', function(){
        try{ if(self.__u && (''+self.__u).indexOf('login-seller')>=0){
          var j=JSON.parse(self.responseText); if(j&&j.sellerNo) window.__sellerNo=j.sellerNo; } }catch(e){}
      });
      return os_.apply(this,arguments);
    };
  } catch(e){}
  try {
    var of=window.fetch;
    window.fetch=function(){ var a=arguments;
      return of.apply(this,a).then(function(r){
        try{ var u=(a[0]&&a[0].url)||a[0];
          if(typeof u==='string'&&u.indexOf('login-seller')>=0){
            r.clone().json().then(function(j){ if(j&&j.sellerNo) window.__sellerNo=j.sellerNo; }); } }catch(e){}
        return r; }); };
  } catch(e){}
})();
"""


def log(m): print(m, flush=True)


def main():
    a = CrawlerAccount.objects.get(login_id=LID, platform='11st')
    d = create_driver(download_dir='/tmp/diag_dl')
    try:
        _ec._try_cookie_login(d, a)
        log(f'로그인 OK: {LID}')
        # 새 문서마다 후킹 주입
        d.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': HOOK})
        d.get('https://soffice.11st.co.kr/view/main')
        sn = None
        for i in range(12):
            time.sleep(2)
            try:
                sn = d.execute_script("return window.__sellerNo")
            except Exception:
                sn = None
            if sn:
                log(f'캡처된 sellerNo={sn} ({(i+1)*2}s)')
                break
        # M_N 비교
        mn = None
        for c in d.get_cookies():
            if c['name'] == 'TP':
                m = re.search(r'M_N(?:%7C|\|)(\d{6,})', c['value'])
                if m: mn = m.group(1)
        log(f'쿠키 M_N={mn} / 캡처 sellerNo={sn} / 일치={str(mn)==str(sn)}')
        if not sn:
            log('캡처 실패'); return
        # 엑셀 그리드 검증
        d.get(f'https://soffice.11st.co.kr/pages/excel-download/?sellerNo={sn}')
        time.sleep(6)
        alert = None
        try:
            al = d.switch_to.alert; alert = al.text; al.accept()
        except Exception:
            pass
        g = ''
        try:
            g = d.execute_script("var x=document.getElementById('popup-body-grid');return x?x.innerText:''") or ''
        except Exception:
            pass
        log(f'그리드 로드 alert={alert}')
        log('그리드: ' + ' | '.join([l for l in g.split('\n') if l.strip()][:8]))
    finally:
        try: d.quit()
        except Exception: pass
        stop_display()


if __name__ == '__main__':
    main()
