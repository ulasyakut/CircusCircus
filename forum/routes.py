from flask import jsonify, render_template, request, redirect, url_for
from flask_login import current_user, login_user, logout_user
from flask_login.utils import login_required
import datetime
from flask import Blueprint, render_template, request, redirect, url_for
from forum.models import User, Post, Comment, Subforum, Message, valid_content, valid_title, db, generateLinkPath, error
from forum.user import username_taken, email_taken, valid_username


##
# This file needs to be broken up into several, to make the project easier to work on.
##

rt = Blueprint('routes', __name__, template_folder='templates')

@rt.route('/action_login', methods=['POST'])
def action_login():
	username = request.form['username']
	password = request.form['password']
	user = User.query.filter(User.username == username).first()
	if user and user.check_password(password):
		login_user(user)
	else:
		errors = []
		errors.append("Username or password is incorrect!")
		return render_template("login.html", errors=errors)
	return redirect("/")


@login_required
@rt.route('/action_logout')
def action_logout():
	#todo
	logout_user()
	return redirect("/")

@rt.route('/action_createaccount', methods=['POST'])
def action_createaccount():
	username = request.form['username']
	password = request.form['password']
	email = request.form['email']
	errors = []
	retry = False
	if username_taken(username):
		errors.append("Username is already taken!")
		retry=True
	if email_taken(email):
		errors.append("An account already exists with this email!")
		retry = True
	if not valid_username(username):
		errors.append("Username is not valid!")
		retry = True
	# if not valid_password(password):
	# 	errors.append("Password is not valid!")
	# 	retry = True
	if retry:
		return render_template("login.html", errors=errors)
	user = User(email, username, password)
	if user.username == "admin":
		user.admin = True
	db.session.add(user)
	db.session.commit()
	login_user(user)
	return redirect("/")


@rt.route('/subforum')
def subforum():
	subforum_id = int(request.args.get("sub"))
	subforum = Subforum.query.filter(Subforum.id == subforum_id).first()
	if not subforum:
		return error("That subforum does not exist!")
	posts = Post.query.filter(Post.subforum_id == subforum_id).order_by(Post.id.desc()).limit(50)
	if not subforum.path:
		subforumpath = generateLinkPath(subforum.id)

	subforums = Subforum.query.filter(Subforum.parent_id == subforum_id).all()
	return render_template("subforum.html", subforum=subforum, posts=posts, subforums=subforums, path=subforumpath)

@rt.route('/loginform')
def loginform():
	return render_template("login.html")


@login_required
@rt.route('/addpost')
def addpost():
	subforum_id = int(request.args.get("sub"))
	subforum = Subforum.query.filter(Subforum.id == subforum_id).first()
	if not subforum:
		return error("That subforum does not exist!")

	return render_template("createpost.html", subforum=subforum)

@rt.route('/viewpost')
def viewpost():
	postid = int(request.args.get("post"))
	post = Post.query.filter(Post.id == postid).first()
	if not post:
		return error("That post does not exist!")
	if not post.subforum.path:
		subforumpath = generateLinkPath(post.subforum.id)
	comments = Comment.query.filter(Comment.post_id == postid).order_by(Comment.id.desc()) # no need for scalability now
	return render_template("viewpost.html", post=post, path=subforumpath, comments=comments)

@login_required
@rt.route('/action_comment', methods=['POST', 'GET'])
def comment():
	post_id = int(request.args.get("post"))
	post = Post.query.filter(Post.id == post_id).first()
	if not post:
		return error("That post does not exist!")
	content = request.form['content']
	postdate = datetime.datetime.now()
	comment = Comment(content, postdate)
	current_user.comments.append(comment)
	post.comments.append(comment)
	db.session.commit()
	return redirect("/viewpost?post=" + str(post_id))

###..sharmin..###

@rt.route('/send_message', methods=['POST', 'GET'])
def send_message():
	if request.method == 'GET':
		return render_template("directmessage.html")
	else:
		data = request.get_json()
		sender_id = data.get('sender_id')
		recipient_id = data.get('recipient_id')
		message = data.get('content')

		sender = User.query.get(sender_id)
		recipient = User.query.get(recipient_id)

		if not sender or not recipient:
			return jsonify({'error': 'Sender or recipient not found'}), 404

		new_message = Message(sender_id=sender_id, recipient_id=recipient_id, message=message)

		db.session.add(new_message)
		db.session.commit()

		return redirect("/messages/1")
	
# Route to fetch messages for a user
@rt.route('/messages/<user_id>', methods=['GET'])
def get_messages(user_id):
    user = User.query.get(user_id)
    if not user:
        return redirect("/")

   # sent_messages = Message.query.filter(sender_id=user.id).all()
   # received_messages = Message.query.filter_by(recipient_id=user.id).all()
    received_messages = Message.query.all()
    print("messages")
    for m in received_messages:
        print(m.message)
    #sent_messages_data = [{'recipient': msg.recipient.username, 'content': msg.content} for msg in sent_messages]
    #received_messages_data = [{'sender': msg.sender.username, 'content': msg.content} for msg in received_messages]

    return render_template("showmessages.html", 
   #     sent_messages = sent_messages_data,
        received_messages = received_messages)
    

if __name__ == '__main__':
    db.create_all()  # Creates database tables if not already created
    rt.run(debug=True)
	

@login_required
@rt.route('/action_post', methods=['POST'])
def action_post():
	subforum_id = int(request.args.get("sub"))
	subforum = Subforum.query.filter(Subforum.id == subforum_id).first()
	if not subforum:
		return redirect(url_for("subforums"))

	user = current_user
	title = request.form['title']
	content = request.form['content']
	#check for valid posting
	errors = []
	retry = False
	if not valid_title(title):
		errors.append("Title must be between 4 and 140 characters long!")
		retry = True
	if not valid_content(content):
		errors.append("Post must be between 10 and 5000 characters long!")
		retry = True
	if retry:
		return render_template("createpost.html",subforum=subforum,  errors=errors)
	post = Post(title, content, datetime.datetime.now())
	subforum.posts.append(post)
	user.posts.append(post)
	db.session.commit()
	return redirect("/viewpost?post=" + str(post.id))

