# -*- coding: utf-8 -*-

import sys
sys.path.append( './python-irc' )

import time
import logging
import httplib2
import urllib
import re
import json
import irc.client
from bs4 import BeautifulSoup
from BufferingBot import BufferingBot, Message

from config import *



max_id = 0


def getHttpContents( url ):
	try:
		http = httplib2.Http()
		res, c = http.request( url )

		if res.status != 200:
			logging.error( 'getHttpContents : %d %s'%( res.status, url ) )
			return None

		if 'err' in res['content-location'] or 'REDIRECT' in res['content-location']:
			logging.error( 'getHttpContents : %s'%url )
			return None

		return BeautifulSoup( c.decode('utf-8') )

	except Exception, e:
		logging.error( 'getHttpContents : %s %s'%( url, e ) )
		return None


def crawlRecent():
	try:
		c = getHttpContents( 'http://toez2dj.net/zeroboard/zboard.php?id=c_market' )
		if c is None:
			return None

		a_tags = [ t.find_all('td')[1].p.a for t in c.select('table table table table table') ][4:]
		a_tags.reverse()

		result = [ { 'id': int(re.search('[0-9]+$', t['href']).group()), 'title': t.string } for t in a_tags ]

		global max_id
		if max_id == 0:
			for r in result:
				if max_id < r['id']:
					max_id = r['id']
			result = []
		else:
			result = [ r for r in result if r['id'] > max_id ]
			for r in result:
				if max_id < r['id']:
					max_id = r['id']

		return result

	except Exception, e:
		logging.error( 'crawlRecent : %s'%e )
		return None


class TOEMarketBot( BufferingBot ):
	def __init__( self, target_chans ):
		server = ( bot_irc_server, bot_irc_port )
		BufferingBot.__init__( self, [server], bot_irc_nickname,
			username = 'toe_market_bot', realname = 'toe_market_bot',
			buffer_timeout = -1, use_ssl = bot_use_ssl )

		self.target_chans = target_chans
		self.connection.add_global_handler( 'welcome', self._on_connected )
		logging.info( 'init end' )

	def _on_connected( self, conn, _ ):
		logging.info( 'connected' )
		self.ircobj.execute_delayed( 2, self._iter_func )

	def _iter_func( self ):
		logging.info( 'iterating...%d' % int(time.time()) )

		result = crawlRecent()
		if result is not None:
			for r in result:
				out_msg = u'\u0002[%s]\u000f %s' % ( r['title'], 'http://toez2dj.net/zeroboard/zboard.php?id=c_market&no='+str(r['id']) )

				for chan in self.target_chans:
					message = Message( 'privmsg', ( chan, out_msg ), timestamp = time.time() )
					self.push_message( message )

		self.ircobj.execute_delayed( 37, self._iter_func )

	def pop_buffer( self, message_buffer ):
		message = message_buffer.peek()
		if message.command in ['privmsg']:
			target = message.arguments[0]
			chan = target.lower()
			if irc.client.is_channel( chan ):
				if chan not in [_.lower() for _ in self.channels]:
					logging.info( 'joinning into... %s' % chan )
					self.connection.join( chan )
		return BufferingBot.pop_buffer( self, message_buffer )


def main():
	logging.basicConfig( level = logging.INFO )

	toe_market_bot = TOEMarketBot( bot_target_chans )
	while True:
		try:
			toe_market_bot.start()
		except KeyboardInterrupt:
			logging.exception( '' )
			break
		except:
			logging.exception( '' )
			raise

if __name__ == '__main__':
	main()
