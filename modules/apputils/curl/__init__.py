# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Github: https://github.com/hapylestat/apputils
#
#

import json
import base64
import gzip
import zlib
import re
from datetime import datetime, timezone
from asyncio.events import AbstractEventLoop
from enum import Enum

from typing import Dict, IO, Mapping, Optional, Tuple, List
from http.client import HTTPResponse
from urllib.request import HTTPPasswordMgrWithDefaultRealm, HTTPBasicAuthHandler, HTTPRedirectHandler, Request, \
  build_opener
from urllib.parse import urlencode
from io import BytesIO
try:
  from urllib.request import URLError, HTTPError
except ImportError:
  from urllib.error import URLError, HTTPError


class CurlRequestType(Enum):
  GET = "GET"
  POST = "POST"
  PUT = "PUT"
  DELETE = "DELETE"


class CURLCookie(object):
  def __init__(self, name: str, value: str):
    """
    :param name: Name of the cookie set by "set-cookie"
    :param value: Cookie value with all params separated by ";"
    """
    self.__EXPIRE_TIME_PATTERN = "%a, %d %b %Y %H:%M:%S %Z"

    self.__name: str = name
    self.__options: Dict[str, str] = {}
    self.__value: str = ""
    self.__expiry_date: datetime or None = None
    if not value:
      return

    options = value.split(";")
    if options:
      self.__value = options[0]

    options = options[1:]
    if options:
      self.__options = {s[0]: s[1] for line in options if "=" in line and (s := line.split("="))}

    if "expires" in self.__options:
      # at the moment we always assume that time are in GMT+0/UTC
      self.__expiry_date = datetime.strptime(self.__options["expires"], self.__EXPIRE_TIME_PATTERN)

  @property
  def name(self) -> str:
    return self.__name

  @property
  def value(self) -> str:
    return self.__value

  @property
  def options(self) -> Dict[str, str]:
    return self.__options

  @property
  def is_expired(self) -> bool:
    if self.__expiry_date:
      return datetime.now(tz=timezone.utc) > self.__expiry_date

    return False

  def __str__(self):
    return f"{self.__name}={self.__value}"


class CURLResponse(object):
  def __init__(self, director_open_result: HTTPResponse or HTTPError, is_stream: bool = False):
    self._code: int = director_open_result.getcode()
    self._headers = director_open_result.info()
    self._is_stream = is_stream
    self._director_result = director_open_result

    if not self._is_stream:
      self._content = director_open_result.read()

  def __decode_response(self, data: bytes or str) -> str:
    data = self.__decode_compressed(data)
    if isinstance(data, bytes) and "Content-Type" in self._headers and "charset" in self._headers["Content-Type"]:
      charset = list(filter(lambda x: "charset" in x, self._headers["Content-Type"].split(';')))
      if len(charset) > 0:
        charset = charset[0].split('=')
        if len(charset) == 2:
          return data.decode(charset[1].lower())
      return data.decode('utf-8')
    elif isinstance(data, bytes):
      return data.decode('utf-8')
    else:
      return data

  def __decode_compressed(self, data: bytes or str):
    if isinstance(data, bytes) and "Content-Encoding" in self._headers:

      if "gzip" in self._headers["Content-Encoding"] or 'x-gzip' in self._headers["Content-Encoding"]:
        data = gzip.GzipFile(fileobj=BytesIO(data)).read()
      elif "deflate" in self._headers["Content-Encoding"]:
        data = zlib.decompress(data)

    return data

  @property
  def code(self):
    """
    :return: HTTP Request Response code
    """
    return self._code

  @property
  def headers(self):
    """
    :return: HTTP Response Headers
    """
    return self._headers

  @property
  def content(self):
    """
    :return: Text content of the response (unzipped and decoded)
    """
    if not self._is_stream:
      return self.__decode_response(self._content)
    else:
      raise TypeError("Stream content could be obtained only via raw property")

  @property
  def raw(self) -> str or HTTPResponse:
    """
    :return: Raw content of the response
    """
    return self._director_result if self._is_stream else self._content

  def from_json(self):
    """
    :return: Return parsed json object from the response, if possible.
             If operation fail, will be returned None

    :rtype dict
    """
    try:
      return json.loads(self.content)
    except ValueError:
      return None

  def response_cookies(self) -> Dict[str, CURLCookie]:
    return {
      value[0]: CURLCookie(*value)
      for item in self._headers.items()
      if item[0].lower() == "set-cookie" and (value := item[1].split("=", maxsplit=1))
    }


class CURLAuth(object):
  def __init__(self, user: str, password: str, force: bool = False, headers: dict = None):
    """
    Create Authorization Object

    :param user: User name
    :param password: Password
    :param force: Generate HTTP Auth headers (skip 401 HTTP Response challenge)
    :param headers: Send additional headers during authorization
    """
    self._user = user
    self._password = password
    self._force = force  # Required if remote doesn't support http 401 response
    self._headers = headers

  @property
  def user(self) -> str:
    return self._user

  @property
  def password(self) -> str:
    return self._password

  @property
  def force(self) -> bool:
    return self._force

  @property
  def headers(self) -> Dict[str, str]:
    if not self._force:
      return self._headers
    else:
      ret_temp = {}
      ret_temp.update(self._headers)
      ret_temp.update(self.get_auth_header())
      return ret_temp

  def get_auth_header(self) -> Dict[str, str]:
    token = base64.encodebytes(bytes(f"{self.user}:{self.password}", encoding='utf8')) \
      .decode("utf-8") \
      .replace('\n', '')
    return {"Authorization": f"Basic {token}"}


class HTTPRedirectFilter(HTTPRedirectHandler):
  def redirect_request(self, req: Request, fp: IO[str], code: int, msg: str,
                       headers: Mapping[str, str], newurl: str) -> Optional[Request]:
    return None


# ToDo: refactor this part
def __encode_str(data) -> bytes:
  return bytes(data, encoding='utf8')


def __detect_str_type(data) -> str:
  """
  :column_type str
  :rtype str
  """
  r = re.search("[^=]+=[^&]*&*", data)  # application/x-www-form-urlencoded pattern
  if r:
    return "application/x-www-form-urlencoded"
  else:
    return "plain/text"


def __parse_content(data) -> Tuple[bytes, Dict[str, str]]:
  if isinstance(data, dict) or isinstance(data, list) or isinstance(data, set) or isinstance(data, tuple):
    response_data = __encode_str(json.dumps(data))
    response_headers = {"Content-Type": "application/json; charset=UTF-8"}
  elif type(data) is str:
    response_data = __encode_str(data)
    response_headers = {
      "Content-Type": f"{__detect_str_type(data)}; charset=UTF-8"
    }
  else:
    response_data = data
    response_headers = {}

  return response_data, response_headers


async def curl_async(loop: AbstractEventLoop,
                     url: str,
                     params: Dict[str, str] = None,
                     auth: CURLAuth = None,
                     req_type: CurlRequestType = CurlRequestType.GET,
                     data: str or bytes or dict = None,
                     headers: Dict[str, str] = None,
                     cookies: List[CURLCookie] = None,
                     timeout: int = None,
                     use_gzip: bool = True,
                     use_stream: bool = False,
                     follow_redirect: bool = True) -> CURLResponse:
  return await loop.run_in_executor(
    None,
    lambda: curl(url, params, auth, req_type, data, headers, cookies, timeout, use_gzip, use_stream, follow_redirect)
  )


def curl(url: str,
         params: Dict[str, str] = None,
         auth: CURLAuth = None,
         req_type: CurlRequestType = CurlRequestType.GET,
         data: str or bytes or dict = None,
         headers: Dict[str, str] = None,
         cookies: List[CURLCookie] = None,
         timeout: int = None,
         use_gzip: bool = True,
         use_stream: bool = False,
         follow_redirect: bool = True) -> CURLResponse:
  """
  Make request to web resource

  :param cookies: list of cookies to send alongside with the request
  :param url: Url to endpoint
  :param params: list of params after "?"
  :param auth: authorization tokens
  :param req_type: column_type of the request
  :param data: data which need to be posted
  :param headers: headers which would be posted with request
  :param timeout: Request timeout
  :param use_gzip: Accept gzip and deflate response from the server
  :param use_stream: Do not parse content of response ans stream it via raw property
  :param follow_redirect Do follow HTTP redirects or not
  :return Response object
  """
  post_req = [CurlRequestType.POST, CurlRequestType.PUT]
  get_req = [CurlRequestType.GET, CurlRequestType.DELETE]

  if params is not None:
    url += "?" + urlencode(params)

  if req_type not in post_req + get_req:
    raise IOError("Wrong request column_type \"%s\" passed" % req_type)

  _headers = {}
  handler_chain = []
  req_args = {
    "headers": _headers
  }

  if req_type in post_req and data is not None:
    _data, __header = __parse_content(data)
    _headers.update(__header)
    _headers["Content-Length"] = len(_data)
    req_args["data"] = _data

  if use_gzip:
    if "Accept-Encoding" in _headers:
      if "gzip" not in _headers["Accept-Encoding"]:
        _headers["Accept-Encoding"] += ", gzip, x-gzip, deflate"
    else:
      _headers["Accept-Encoding"] = "gzip, x-gzip, deflate"

  if auth is not None and auth.force is False:
    manager = HTTPPasswordMgrWithDefaultRealm()
    manager.add_password("", url, auth.user, auth.password)
    handler_chain.append(HTTPBasicAuthHandler(manager))

  if auth is not None and auth.force:
    _headers.update(auth.headers)

  if headers is not None:
    _headers.update(headers)

  if cookies and _headers:
    temp_cookies: List[str] = list([str(cookie) for cookie in cookies if not cookie.is_expired])
    if "cookie" in _headers:
      temp_cookies.extend(_headers["cookie"].split("; "))

    _headers["cookie"] = "; ".join(temp_cookies)

  if not follow_redirect:
    handler_chain.append(HTTPRedirectFilter)

  director = build_opener(*handler_chain)
  req = Request(url, **req_args)
  req.get_method = lambda: req_type.value

  try:
    if timeout is not None:
      return CURLResponse(director.open(req, timeout=timeout), is_stream=use_stream)
    else:
      return CURLResponse(director.open(req), is_stream=use_stream)
  except URLError or HTTPError as e:
    if isinstance(e, HTTPError):
      return CURLResponse(e, is_stream=use_stream)
    else:
      raise TimeoutError
