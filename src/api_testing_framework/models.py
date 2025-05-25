from typing import List, Optional

from pydantic import BaseModel


class Artist(BaseModel):
    id: str
    name: str


class Image(BaseModel):
    url: str
    height: Optional[int]
    width: Optional[int]


class Album(BaseModel):
    album_type: str
    artists: List[Artist]
    id: str
    name: str
    release_date: str
    total_tracks: int
    images: List[Image]


class PagingAlbums(BaseModel):
    href: str
    items: List[Album]
    limit: int
    next: Optional[str]
    offset: int
    previous: Optional[str]
    total: int


class NewReleasesResponse(BaseModel):
    albums: PagingAlbums


class Track(BaseModel):
    id: str
    name: str
    album: Album
    artists: List[Artist]
    popularity: int
    preview_url: Optional[str]


class TopTracksResponse(BaseModel):
    tracks: List[Track]
