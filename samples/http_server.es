
# TODO: operator :- i.e. [:-1]
import re
import http.server
import socketserver
import json
import uuid

# curl -X POST -H 'application/json' --data-binary '{"spk":"8"}' 'http://localhost:8080/user'
# curl 'http://localhost:8080/user/8'

# Handler = http.server.SimpleHTTPRequestHandler
#
# class Handler(http.server.BaseHTTPRequestHandler) {
#    do_GET = (self) => {}
# }
#

class Response() {
    __init__(self, status_code=200) => {
        super().__init__();
        self.status_code = status_code
        self.headers = {:}
        self.payload=b""
        return
    }
}

class JsonResponse(Response) {
    __init__(self, obj, status_code=200) => {
        super().__init__(status_code);
        self.headers = {"Content-Type": "application/json"}
        self.payload=json.dumps(obj).encode('utf-8') + b"\n"
        return
    }
}

patternToRegex(pattern) => {
    # convert a url pattern into a regular expression
    #
    #   /abc        - match exactly
    #   /:abc       - match a path compenent exactly once
    #   /:abc?      - match a path component 0 or 1 times
    #   /:abc+      - match a path component 1 or more times
    #   /:abc*      - match a path component 0 or more times
    #
    # /:abc will match '/foo' with
    #  {'abc': foo}
    # /:bucket/:key* will match '/mybucket/dir1/dir2/fname' with
    #  {'bucket': 'mybucket', key: 'dir1/dir2/fname'}

    parts = [part for part in pattern.split("/") if part]
    tokens = []
    re_str = "^"
    for part in parts {
        re_str += '\\/'
        if (part.startswith(':')) {
            c = part[-1]
            if c == '?' {
                tokens.append(part[1: -1])
                re_str += "([^\\/]*)"
            } else if c == '*' {
                tokens.append(part[1: -1])
                re_str += "(.+)"
            } else if c == '+' {
                tokens.append(part[1: -1])
                re_str += "(.+)"
            } else {
                tokens.append(part[1:])
                re_str += "([^\\/]+)"
            }
        } else {
            re_str += part
        }
    }
    if re_str != "^\\/" {
        re_str += "\\/?"
    }
    re_str += '$'
    return (re.compile(re_str), tokens)
}

class Database() {
    __init__(self) => {
        super().__init__();

        self._tables = {:}
        return
    }

    createTable(self, table) => {
        self._tables[table] = {:}
    }

    selectAll(self, table) => {
        return list(self._tables[table].values())
    }

    selectBySPK(self, table, spk) => {
        return self._tables[table][spk]
    }

    insertBySPK(self, table, spk, record) => {
        if spk === None {
            spk = str(uuid.uuid4())
        }
        record['spk'] = spk
        self._tables[table][spk] = record
    }

    deleteBySPK(self, table, spk) => {
        raise NotImplementedError()
    }
}

class Resource() {
    __init__(self) => {
        super().__init__()
        return
    }
    endpoints(self) => {
        return []
    }
}

class UserResource(Resource) {
    __init__(self, db) => {
        super(UserResource, self).__init__();
        self.db = db
        return
    }

    endpoints(self) => {
        return [
            ('GET', '/user', self.get_users),
            ('POST', '/user', self.create_user),
            ('GET', '/user/:spk', self.get_user),
            ('POST', '/user/:spk', self.update_user)
            ('DELETE', '/user/:spk', self.delete_user)
        ]
    }

    get_users(self, request, location, matches) => {
        data = self.db.selectAll('users')
        return JsonResponse(data)
    }

    create_user(self, request, location, matches) => {
        obj = request.json()
        spk = self.db.insertBySPK('users', obj->spk, obj)
        data = {'result': {'spk': spk}}
        return JsonResponse(data)
    }

    get_user(self, request, location, matches) => {
        data = self.db.selectBySPK('users', matches['spk'])
        return JsonResponse(data)
    }

    update_user(self, request, location, matches) => {
        data = self.db.selectBySPK('users', matches['spk'])
        new_data = data[:]
        new_data.update(request.json())
        self.db.insertBySPK('users', matches['spk'], new_data)
        return JsonResponse({'result': {'spk': matches['spk']}})
    }

    delete_user(self, request, location, matches) => {
        success = self.db.deleteBySPK('users', matches['spk'])
        code = (if success 200 else 404)
        data = {'result': {'spk': matches['spk']}}
        return JsonResponse(data, code)
    }
}

class Router() {
    __init__(self) => {
        super(Router, self).__init__();
        self.route_table = {
            "DELETE": [],
            "GET": [],
            "POST": [],
            "PUT": [],
        }
        return
    }

    registerEndpoints(self, endpoints) => {
        for method, pattern, callback in endpoints {
            regex, tokens = patternToRegex(pattern)
            self.route_table[method].append((regex, tokens, callback))
        }
    }

    getRoute(self, method, path) => {

        for re_ptn, tokens, callback in self.route_table[method] {
            m = re_ptn.match(path)
            if m {
                return callback, {k: v for k, v in zip(tokens, m.groups())}
            }
        }
        return None
    }
}

class RequestHandler(http.server.BaseHTTPRequestHandler) {

    _router = None

    __init__(self, *args) => {
        super(RequestHandler, self).__init__(*args);
        return
    }

    _handleMethod(self, method) => {
        if result = RequestHandler._router.getRoute(method, self.path) {
            # TODO: try-block around user code
            callback, matches = result
            response = callback(self, self.path, matches)

            if !response {
                response = JsonResponse({'error':
                    'endpoint failed to return a response'}, 500)
            }

        } else {
            response = JsonResponse({'error': 'path not found'}, 404)
        }

        self.send_response(response.status_code)
        for k, v in response.headers.items() {
            self.send_header(k, v)
        }
        self.end_headers()
        self.wfile.write(response.payload)
    }

    do_DELETE(self) => {self._handleMethod('DELETE')}
    do_GET(self) => {self._handleMethod('GET')}
    do_POST(self) => {self._handleMethod('POST')}
    do_PUT(self) => {self._handleMethod('PUT')}

    json(self) => {
        length = int(self.headers?.['content-length'])
        binary_data = self.rfile.read(length)
        obj = json.loads(binary_data.decode('utf-8'))
        return obj
    }
}

main = (args) => {
    HOST="0.0.0.0"
    PORT=8081

    g_database = Database()
    g_database.createTable('users')
    g_database.insertBySPK('users', '1', {'username': 'test1'})
    g_database.insertBySPK('users', '2', {'username': 'test2'})
    g_database.insertBySPK('users', '3', {'username': 'test3'})
    g_router = Router()
    g_user_resource = UserResource(g_database)
    g_router.registerEndpoints(g_user_resource.endpoints())

    RequestHandler._router = g_router

    with httpd=socketserver.TCPServer((HOST, PORT), RequestHandler) {
        print(f"listening on ${HOST}:${PORT}")
        httpd.serve_forever()
    }
}


