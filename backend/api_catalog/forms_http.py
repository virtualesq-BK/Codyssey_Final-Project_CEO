"""공개 페이지/첨부용 HTTP. 비공개 주소 및 허용되지 않은 리다이렉트 차단."""
import ipaddress
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

class FetchError(RuntimeError):
    pass

def verify_url(url, allowed):
    u=urllib.parse.urlsplit(url);host=(u.hostname or '').lower()
    if u.scheme not in ('http','https') or u.username or u.password or not any(host==h or host.endswith('.'+h) for h in allowed):
        raise FetchError('허용되지 않은 URL/호스트')
    if u.port and u.port not in (80,443):raise FetchError('표준 HTTP 포트만 지원')
    try:
        addresses=socket.getaddrinfo(host,u.port or (443 if u.scheme=='https' else 80))
        if any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):raise FetchError('비공개 네트워크 주소는 지원하지 않음')
    except socket.gaierror:
        # An explicitly configured HTTP(S) proxy can resolve the allowlisted host remotely.
        if not urllib.request.getproxies().get(u.scheme):raise FetchError('호스트 이름 조회 실패') from None

class Redirects(urllib.request.HTTPRedirectHandler):
    def __init__(self,allowed):self.allowed=allowed
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        verify_url(newurl,self.allowed)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

class Client:
    def __init__(self,allowed=('k-startup.go.kr',)):
        self.allowed=tuple(allowed);self.opener=urllib.request.build_opener(Redirects(self.allowed))
    def get(self,url,limit=25*1024*1024):
        verify_url(url,self.allowed)
        for attempt in range(3):
            time.sleep(.3)
            try:
                req=urllib.request.Request(url,headers={'User-Agent':'NadosajangAttachments/1.0 public-document-collector'})
                with self.opener.open(req,timeout=30) as r:
                    data=r.read(limit+1)
                    if len(data)>limit:raise FetchError('응답 크기 상한 초과')
                    return data,dict(r.headers),r.geturl()
            except urllib.error.HTTPError as exc:
                if exc.code not in (429,500,502,503,504) or attempt==2:raise FetchError(f'HTTP {exc.code}: 다운로드 제한/원문 상태 확인 필요') from None
            except (urllib.error.URLError,TimeoutError,OSError):
                if attempt==2:raise FetchError('네트워크 요청 실패') from None
            time.sleep(2**attempt)
        raise FetchError('재시도 실패')
