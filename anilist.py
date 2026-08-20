import httpx 

anilist_url = "https://graphql.anilist.co"

query = """
query ($search: String) {
  Media(search: $search, type: MANGA) {
    id
    title {
      romaji
      english
    }
    genres 
    chapters 
    description
    coverImage {
      large
    }
    averageScore
  }
}
"""

def search_manga(search_term: str):
    response = httpx.post(              #Step 1: Send request/get request back
        anilist_url,
        json={"query": query, "variables": {"search": search_term}}
    )
    data = response.json()      #Step 2: Open request/gather
    return data["data"]["Media"]       # Step 3: grab the part requested for (data, media)


list_query = """
query ($sort: [MediaSort]) {
  Page(perPage: 10) {
    media(type: MANGA, sort: $sort) {
      id
      title {
        romaji
        english
      }
      coverImage {
        large
      }
      averageScore
    }
  }
}
"""

list_query_by_country = """
query ($sort: [MediaSort], $country: CountryCode) {
  Page(perPage: 10) {
    media(type: MANGA, sort: $sort, countryOfOrigin: $country) {
      id
      title {
        romaji
        english
      }
      coverImage {
        large
      }
      averageScore
    }
  }
}
"""

def get_manga_list(sort: str, country: str = None):
    try:
        if country:
            response = httpx.post(
                anilist_url,
                json={
                    "query": list_query_by_country,
                    "variables": {"sort": [sort], "country": country}
                },
                timeout=10
            )
        else:
            response = httpx.post(
                anilist_url,
                json={
                    "query": list_query,
                    "variables": {"sort": [sort]}
                },
                timeout=10
            )
        data = response.json()
        return data["data"]["Page"]["media"]
    except (httpx.ReadTimeout, TypeError, KeyError):
        return []

anime_query = """ 
query($search: String) { 
  Media(search: $search, type: ANIME) { 
    id 
    title { 
      romaji
      english
    }
    genres
    episodes 
    description 
    coverImage {
      large 
    }
    averageScore 
  }
}
"""

anime_list_query = """
query ($sort: [MediaSort]) {
  Page(perPage: 10) {
    media(type: ANIME, sort: $sort) {
      id
      title {
        romaji
        english
      }
      coverImage {
        large
      }
      averageScore
    }
  }
}
"""

def search_anime(search_term: str):
    response = httpx.post( 
        anilist_url, 
        json={"query": anime_query, "variables": {"search": search_term}}
    )
    data = response.json()
    return data["data"]["Media"]

def get_anime_list(sort: str):
    try:
        response = httpx.post(
            anilist_url,
            json={"query": anime_list_query, "variables": {"sort": [sort]}},
            timeout=10
        )
        data = response.json()
        return data["data"]["Page"]["media"]
    except (httpx.ReadTimeout, TypeError, KeyError):
        return []

details_query = """
query ($id: Int, $type: MediaType) {
  Media(id: $id, type: $type) {
    id
    title {
      romaji
      english
    }
    genres
    chapters
    episodes
    description
    coverImage {
      large
    }
    averageScore
  }
}
"""

def get_details(media_id: int, media_type: str):
    response = httpx.post(
        anilist_url,
        json={
            "query": details_query,
            "variables": {"id": media_id, "type": media_type}
        }
    )
    data = response.json()
    return data["data"]["Media"]