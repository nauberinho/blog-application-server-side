# Imports
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField
from flask_graphql import GraphQLView
from flask_cors import CORS
from termcolor import colored
from datetime import date

basedir = os.path.abspath(os.path.dirname(__file__))

# App Initialization
app = Flask(__name__)
CORS(app)
app.debug = True

# Configs
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_COMMIT_ON_TEARDON'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

# Modules
db = SQLAlchemy(app)

# Models
class User(db.Model):
    __tablename__ = 'users'

    uuid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(256), index=True, unique=True)
    posts = db.relationship('Post', backref='author')
    # created = db.Column(db.String)

    def __repr__(self):
        return '<User %r>' % self.username

class Post(db.Model):
    __tablename__ = 'posts'

    uuid = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), index=True)
    body = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey('users.uuid'))
    # created = db.Column(db.String)

    def __repr__(self):
        return '<Post %r>' % self.title

# Schema Objects
class PostObject(SQLAlchemyObjectType):
    class Meta:
        model = Post
        interfaces = (graphene.relay.Node, )

class UserObject(SQLAlchemyObjectType):
    class Meta:
        model = User
        interfaces = (graphene.relay.Node, )

class Query(graphene.ObjectType):
    node = graphene.relay.Node.Field()

    all_posts = SQLAlchemyConnectionField(PostObject)
    post = graphene.Field(PostObject, uuid = graphene.String())
    def resolve_post(self, info, uuid):
        query = PostObject.get_query(info)
        return query.filter(Post.uuid == uuid).first()

    all_users = SQLAlchemyConnectionField(UserObject)
    user = graphene.Field(UserObject, uuid = graphene.String())
    def resolve_user(self, info, uuid):
        query = UserObject.get_query(info)
        return query.filter(User.uuid == uuid).first()

    

class CreatePost(graphene.Mutation):
    class Arguments:
        title = graphene.String(required=True)
        body = graphene.String(required=True) 
        username = graphene.String(required=True)

    post = graphene.Field(lambda: PostObject)

    def mutate(self, info, title, body, username):
        user = User.query.filter_by(username=username).first()
        post = Post(title=title, body=body)

        if user is not None:
            post.author = user
            # post.created = date.today()

        db.session.add(post)
        db.session.commit()

        return CreatePost(post=post)

class CreateUser(graphene.Mutation):
    class Arguments:
        username = graphene.String(required=True)

    user = graphene.Field(lambda: UserObject)

    def mutate(self, info, username):
        user_exists = (User.query.filter_by(username=username).first()) is not None

        if not user_exists:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()

        return CreateUser(user=user)

class Mutation(graphene.ObjectType):
    create_post = CreatePost.Field()
    create_user = CreateUser.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)

# Routes
app.add_url_rule(
    '/graphql',
    view_func=GraphQLView.as_view(
        'graphql',
        schema=schema,
        graphiql=True # enables access to the GraphiQL interface
    )
)

@app.route('/')
def index():
    return '<p> Hello World!</p>'

if __name__ == '__main__':
    app.run()