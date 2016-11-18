import os
import re
import urllib2

import jinja2
import webapp2
from google.appengine.ext import db


USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")

PAGES = {
	'main': "main.html",
	'blog': "blog.html",
	'lonepost': "lonepost.html",
	'newpost': "newpost.html",
	'signup': "signup.html",
}


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
			Render template.

			Arguments:
				template: to render (ex: "page.html")
				data: key:values to populate template.
			Output:
				write page.
		"""

		t = jinja_env.get_template(template)
		self.response.headers.add_header(
			'Cache-Control',
			'max-age=6000',
		)

		self.response.out.write(t.render(data))


	def grab(self, *args):
		"""
			Grab request parameters.

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
	"""
		Display a single article.

		arguments:
			article_id: the post id in the datastore
		outputs:

	"""

	def get(self, article_id):
		data = {'article': Article.get_by_id(int(article_id))}
		self.render(PAGES['lonepost'], data)


class BlogHandler(Handler):
	"""
		Blog handler
	"""
	
	def get(self):

		data = {
			'articles': self.fetch_articles(),
			'visits': self.count_visits(),
		}

		self.response.headers.add_header(
			'Set-Cookie',
			'visits={}'.format(data['visits'])
		)

		self.render(PAGES['blog'], data)


	def fetch_articles(self):
		return db.GqlQuery('SELECT * FROM Article ORDER BY created DESC')

	def count_visits(self):
		return (1 + int(self.request.cookies.get('visits', '0')))


class SignupHandler(Handler):

	def get(self):
		self.render(PAGES['signup'])

	def post(self):

		data = self.grab(
			'username',
			'password',
			'verify',
			'email',
		)

		if data['password'] != data['verify']:
			data['verify_error'] = 'Passwords must match'
			self.render(PAGES['signup'], data)

class NewPostHandler(Handler):
	"""
		Handler for new blog post page.
		Redirects to post permalink once submitted.
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
	[
	('/', MainPage),
	('/blog/?', BlogHandler),
	('/blog/newpost', NewPostHandler),
	('/blog/([0-9]+)', PostHandler),
	('/blog/signup', SignupHandler),
	],
	debug=True)
