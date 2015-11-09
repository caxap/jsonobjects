#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests
import jsonobjects as jo


class iTunesAppSchema(jo.Schema):
    id = jo.IntegerField('trackId')
    url = jo.Field('trackViewUrl')
    name = jo.StringField('trackName')
    currency = jo.StringField()
    price = jo.FloatField(min_value=0.0)
    rating = jo.FloatField('averageUserRating')
    reviews = jo.IntegerField('userRatingCountForCurrentVersion')
    version = jo.StringField()
    publisher_id = jo.IntegerField('artistId')
    publisher_url = jo.Field('artistViewUrl')
    publisher_name = jo.StringField('artistName')
    categories = jo.ListField('genres', child=jo.StringField())
    icon = jo.Field(
        ['artworkUrl512', 'artworkUrl60'], post_process=lambda v: {'url': v})
    screenshots = jo.ListField(
        'screenshotUrls', child=jo.Field(post_process=lambda v: {'url': v}))


parser = iTunesAppSchema('results[0]')


@parser.as_decorator
def get_app_details(app_id):
    url = 'https://itunes.apple.com/lookup?id={}'
    return requests.get(url.format(app_id)).json()


if __name__ == '__main__':
    details = get_app_details(880047117)  # https://itunes.apple.com/lookup?id=880047117
    print(json.dumps(details,
                     indent=2,
                     sort_keys=True,
                     separators=(',', ': ')))
