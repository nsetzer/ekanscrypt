

import requests


url = 'https://jsonplaceholder.typicode.com'


getPosts = () => {
    response = requests.get(url + "/posts");
    if (response.status_code != 200) {
        return None;
    }
    print(response.status_code)
    return response.json()
}

getPost = (index) => {
    response = requests.get(url + f"/posts/${index}" );
    if (response.status_code != 200) {
        return None;
    }
    print(response.status_code)
    return response.json()
}

getPostComments = (index) => {
    response = requests.get(url + "/posts/${index}/comments" );
    if (response.status_code != 200) {
        return None;
    }
    print(response.status_code)
    return response.json()
}

#posts = getPosts()
#if posts {
#    for post in posts {
#        print(post->title)
#    }
#}

print(getPostComments(1))