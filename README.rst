jsonobjects
==============

``jsonobjects`` allows you to declaratively specify how to extract and convert elements from a JSON document.


Installation
------------
We recommend the use of `virtualenv <https://virtualenv.pypa.io/>`_ and of
`pip <https://pip.pypa.io/>`_. You can then use ``pip install -U jsonobjects``.
You may also have `setuptools <http://peak.telecommunity.com/DevCenter/setuptools>`_ and thus
you can use ``easy_install -U jsonobjects``. Otherwise, you can download the
source from `GitHub <http://github.com/caxap/jsonobjects>`_ and run ``python
setup.py install``.


Dependencies
------------
All dependencies are optional.

- `JMESPath <https://jmespath.readthedocs.org/en/latest/>`_ to allow advanced queries (see `JMESPath <https://jmespath.readthedocs.org/en/latest/>`_ documentation for details).
- `dateutil <https://dateutil.readthedocs.org/en/latest/>`_ to allow iso-8601 date formats.


Usage
-----

Example of schema to parse iTunes lookup response for software item:

.. code:: python

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

    # https://itunes.apple.com/lookup?id=880047117
    details = get_app_details(880047117)
    print(details)

The code above produces next result:

.. code:: python

    {
      "categories": ["Games", "Puzzle", "Action"],
      "currency": "USD",
      "icon": {"url": "http://is3.mzstatic.com/image/thumb/Purple3/v4/27/f0/d9/27f0d923-e00b-5f2c-a1e9-235ed3f83d14/source/512x512bb.jpg"},
      "id": 880047117,
      "name": "Angry Birds 2",
      "price": 0.0,
      "publisher_id": 298910979,
      "publisher_name": "Rovio Entertainment Ltd",
      "publisher_url": "https://itunes.apple.com/us/developer/rovio-entertainment-ltd/id298910979?uo=4",
      "rating": 4.0,
      "reviews": 4796,
      "screenshots": [
        {"url": "http://a4.mzstatic.com/us/r30/Purple3/v4/5c/5e/54/5c5e542c-54a1-7812-12df-045aca3ebb86/screen1136x1136.jpeg"},
        {"url": "http://a1.mzstatic.com/us/r30/Purple3/v4/95/50/db/9550dbba-9cbf-d588-fac4-5ebf04614023/screen1136x1136.jpeg"},
        {"url": "http://a5.mzstatic.com/us/r30/Purple3/v4/22/ef/e7/22efe7c2-bd05-6f58-f176-92e7230853bd/screen1136x1136.jpeg"},
        {"url": "http://a2.mzstatic.com/us/r30/Purple69/v4/72/44/ba/7244ba34-6c8c-5dc5-38e4-e134a97cd0d1/screen1136x1136.jpeg"},
        {"url": "http://a5.mzstatic.com/us/r30/Purple6/v4/1b/e4/98/1be49811-f5be-cb3f-1a31-a20b5f5663ee/screen1136x1136.jpeg"}
      ],
      "url": "https://itunes.apple.com/us/app/angry-birds-2/id880047117?mt=8&uo=4",
      "version": "2.2.1"
    }

See tests.py for more examples.


Tests
-----
Getting the tests running looks like:

.. code-block:: shell

    # Install dependencies
    $ pip install -r requirement.txt
    # Run the test suites
    $ python tests.py

License
-------

The MIT License (MIT)

Contributed by `Maxim Kamenkov <https://github.com/caxap/>`_
