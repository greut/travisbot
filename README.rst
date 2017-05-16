============
 Travis Bot
============

.. image:: https://travis-ci.org/greut/travisbot.svg?branch=master
   :target: https://travis-ci.org/greut/travisbot

.. image:: https://img.shields.io/pypi/dd/discord-travisbot.svg
   :target: https://pypi.python.org/pypi/discord-travisbot

.. image:: https://img.shields.io/github/stars/greut/travisbot.svg
   :target: https://github.com/greut/travisbot/stargazers

A bot for Discord. (Work in progress)

Development
===========

To setup and run the basic steps of the bot.

Installation
------------

.. code-block:: console

    $ python -m venv .
    $ . bin/activate
    (travisbot)$ pip install -e .[fast]

Running
-------

The secret token is read from the environment variables.

.. code-block:: console

    (travisbot)$ export TOKEN=...
    (travisbot)$ python -m travisbot

Release
=======

Update the version number and clean up the ``dist`` directory before-hand.

.. code-block:: console

    (travisbot)$ python setup.py register -r https://pypi.python.org/pypi
    (travisbot)$ pip install wheel twine
    (travisbot)$ python setup.py bdist_wheel
    (travisbot)$ twine upload dist/*

Bibliography
============

- `A Discord bot with asyncio <https://tutorials.botsfloor.com/a-discord-bot-with-asyncio-359a2c99e256>`_
- `Discord API Reference <https://discordapp.com/developers/docs/reference>`_
- `discord.py <https://github.com/Rapptz/discord.py>`_
