"""
	Google App Engine Fun (gaefun) stemmed from the CS253 Udacity course.
	The course is about Web Development, not about Python. I rewrite the 
	code to incorporate the knowledge I glean here and there to make it 
	better with respect to Python, and good practices as I learn them.
"""
import hmac
import os
import re
import urllib2

import jinja2
import webapp2
from google.appengine.ext import db

__title__ = 'gaefun'
__version__ = '1.0'
__author__ = 'Jugurtha Hadjar'
__license__ = 'Apache 2.0'
__copyright__ = 'Copyright 2016'


# Regular expressions for form input validation from CS253. Too limiting though.
# TODO: Improve w/ https://www.owasp.org/index.php/Input_Validation_Cheat_Sheet.

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")


SECRET = "tl;dr: This is the rythm of the night."
PAGES = {
	'main': "main.html",
	'blog': "blog.html",
	'lonepost': "lonepost.html",
	'newpost': "newpost.html",
	'signup': "signup.html",
	'404': "404.html",
}

URLS = [
	# Using "lazy handlers" as per: http://webapp2.readthedocs.io/en/latest/
	# guide/routing.html#guide-routing-lazy-handlers

	# This is normally done post handler definitions or it raises a NameError.

	# I want the URIs and their handlers to be at the top so a reader can have
	# see the big picture of what URI is handled by which handler as opposed to
	# having this at the bottom as in the usual way. One inconvenience of this 
	# is that I had to prefix with 'hello.' because I couldn't figure out a way
	# to make forward declarations not ugly.

	# TODO: Find a better way to make it look like this ('/', 'MainPage')

	('/', 'hello.MainPage'),
	('/blog/?', 'hello.BlogHandler'),
	('/blog/newpost', 'hello.NewPostHandler'),
	('/blog/([0-9]+)', 'hello.PostHandler'),
	('/signup', 'hello.SignupHandler'),
	
]


# Set execution environment: current directory, static files, etc.

patterns = os.getcwd() + '/patterns'
jinja_env = jinja2.Environment(
	loader = jinja2.FileSystemLoader(patterns),
	autoescape = True,
)


class Handler(webapp2.RequestHandler):
	"""
		Handler for rendering templates.
	"""

	def render(self, template, data={}):
		"""
			Render `template` populated with `data`.

			Arguments:
				template: to render (ex: "page.html")
				data: key:values to populate template.
			Output:
				rendering.
		"""

		t = jinja_env.get_template(template)
		self.response.headers.add_header(
			'Cache-Control',
			'public; max-age=6000',
		)

		self.response.out.write(t.render(data))


	def grab(self, *args):
		"""
			Grab request parameters and make a dictionary out of them.
			Why:
				- Usual way is to do this whenever we need to get params:
					username = self.request.get('username')
					password = self.request.get('password')

				- I want to make it simpler:
					data = grab('username', 'password')

			Arguments:
				parameter names
			Output:

		"""
		return {arg : self.request.get(arg, '') for arg in iter(args)}


class MainPage(Handler):
	"""
		Home page handler
	"""

	def get(self):
		self.render(PAGES['main'])


class PostHandler(Handler):

	def get(self, article_id):
		"""
			Display a single article.

			arguments:
				article_id: the post id in the datastore
			output: render single article
		"""

		data = {
			'article': Article.get_by_id(int(article_id)),
		}

		self.render(PAGES['lonepost'], data)


class BlogHandler(Handler):
	"""
		Display the blog in its entirety.
	"""
	
	def get(self):

		data = {
			'articles': self.fetch_articles(),
		}

		# Forgive me Lord for what I am about to write..
		self.response.headers.add_header(
			'Set-Cookie',
			'visits={}'.format(self.count_visits())
		)

		self.render(PAGES['blog'], data)


	def fetch_articles(self):
		return db.GqlQuery('SELECT * FROM Article ORDER BY created DESC')

	def parse_cookie(self):
		visits = 0
		try:
			value, value_hash = self.request.cookies.get('visits').split('|')

			good_cookie = self.check_secure_val(value, value_hash)
			
		except ValueError:
			return 1
		finally:
			visits += 1
			return visits



	def count_visits(self):
		"""
				cookie format: visits=9|00df17ab7a4e013ea9811e0b9e2436b8
				The number of visits before the pipe. The hash after the pipe.
		"""

		try:
			value, value_hash = self.request.cookies.get('visits').split('|')

		except ValueError:
			return 1



		# cookie_value = self.request.cookies.get('visits', '0')


	def make_secure_val(self, value):
		return hmac.new(SECRET, value).hexdigest()

	def check_secure_val(self, value, value_hash):
		"""
			For a given pair value, hash provided by the user, check that the
			computed hash of this value correspond to the user provided hash.

			Arguments:
				- value: the value we're interested in.
				- value_hash: the hash of the value.

			Output:
				- Boolean of comparison between computed and provided hash.
		"""
		# Original is check_secure_val(h) and then splitting at the pipe '|'
		# I think it's better to avoid assumptions about format and stick to 
		# what we know won't change: we're comparing two values.
		# I was going to do:	
		#	return (SECRET + value).hexdigest() == value_hash
		# But according to https://docs.python.org/2/library/hmac.html:
		# Warning: When comparing the output of hexdigest() to an 
		# externally-supplied digest during a verification routine, it is 
		# recommended to use the compare_digest() function instead of 
		# the == operator to reduce the vulnerability to timing attacks.

		return hmac.compare_digest(value, value_hash)

class SignupHandler(Handler):
	"""
		Handler for user signup/registration.
	"""

	def get(self):
		"""
			Render signup page.
		"""
		self.render(PAGES['signup'])

	def post(self):
		"""
			Handle signup form.
		"""

		data = self.grab(
			'username',
			'password',
			# 'verify',
			'email',
		)



	def verify(self, data):
		pass
		# TODO: Signup verifications not yet complete. 
		#		Toy a bit with that and App Engine's "users".

class User(db.Model):
	username = db.StringProperty(required=True)
	password = db.StringProperty(required=True)
	email = db.EmailProperty()


class NewPostHandler(Handler):
	"""
		Handler for new blog post submission page.
		Once the post is submitted, redirects to its permalink.
	"""

	def get(self):
		self.render(PAGES['newpost'])

	def post(self):

		data = self.grab('title', 'body')

		if len(data) != 2:
			data['error'] = 'Title *and* body'
			self.render(PAGES['newpost'], data)

		a = Article(
			title=data['title'],
			body=data['body'],
		)
		a.put()
		permalink = str(a.key().id())
		self.redirect('/blog/{}'.format(permalink))


class Article(db.Model):
	title = db.StringProperty(required=True)
	body = db.TextProperty(required=True)
	created = db.DateTimeProperty(auto_now_add=True)


app = webapp2.WSGIApplication(
	URLS,
	debug=True,
	config={
		'hash_secret': SECRET,
	})
