from functools import wraps
from flask import Flask, jsonify, request
from pymongo import MongoClient
import datetime
import jwt
import bcrypt
from bson import ObjectId

connection_string = 'mongodb+srv://sikandarnust1140:ZBXI5No3tsTeKb0u@cluster0.mo69b0z.mongodb.net/newDB?retryWrites=true&w=majority'
client = MongoClient(connection_string)

#databases
database = client['Authentication']
database2 = client['userCollection']

#collections
collection = database2['user']
posts_collection= database['posts_collection']

app = Flask(__name__)
app.config['SECRET_KEY'] = "your_secret_key_here"



def token_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        token = request.headers.get("x-access-token")
        if not token:
            return jsonify({"message": "Token not found"}), 400
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = collection.find_one({"_id": ObjectId(data['_id'])})
            if not current_user:
                return jsonify({"message": "Invalid token"}), 401
        except:
            return jsonify({"message": "Error in decoding token"}), 401
        return func(current_user, *args, **kwargs)
    return decorated

# user authentication routes

@app.route("/register", methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return jsonify({"error": "Missing data"}), 404

    hashed_pwd = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    user_data = {
        "username": username,
        "password": hashed_pwd,

    }

    try:
        collection.insert_one(user_data)
        return jsonify({"message": "SignUp successfully"}), 200
    except Exception as e:
        return jsonify({"error": "SignUp Unsuccessful"}), 500


@app.route("/login", methods=['POST'])
def Login():
    username = request.form.get('username')
    password = request.form.get('password')

    try:
        document = collection.find_one({"username": username})
        if not document:
            return jsonify("Do not find user name ")

        if bcrypt.checkpw(password.encode("utf-8"),document['password']):

            token = jwt.encode({
                "_id": str(document['_id']),
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            }, app.config['SECRET_KEY'], algorithm="HS256")
            return jsonify({"Token": token}), 200
        else:
            return jsonify({"error": "login Unsuccessful"}), 401
    except Exception as e:
        return jsonify({"error": "login unnsuccessful"}), 500



# Post management rutes
@app.route("/post", methods=['POST'])
@token_required
def create_post(current_user):
    data = request.json
    title = data.get("title")
    text = data.get("text")
    tags = data.get("tags")
    thumbnail = data.get("thumbnail")
    comments = data.get("comments")

    if not title or not text or not tags or not thumbnail:
        return jsonify({"error": "Invalid input"}), 400

    post_data = {
        "title": title,
        "text": text,
        "tags": [tags] if isinstance(tags, str) else tags,
        "thumbnail": [thumbnail] if isinstance(thumbnail, str) else thumbnail,
        "comments" : [comments] if isinstance(comments, str) else comments,
        "likes" : 0,
        "dislikes" : 0,
        "created_at": datetime.datetime.utcnow()
    }

    try:
        posts_collection.insert_one(post_data)
        return jsonify({"message": "Post created successfully"}), 201
    except Exception as e:
        return jsonify({"error": "Post creation failed"}), 500


@app.route('/post', methods=['GET'])
@token_required
def get_post(current_user):
    id = request.json.get("id")
    try:
        post = posts_collection.find_one({'_id': ObjectId(id)})
        if post:
            post['_id'] = str(post['_id'])
            return jsonify(post), 200
        else:
            return jsonify({'error': 'Post not found'}),404
    except Exception as e:
        return jsonify({'Error': str(e)}), 500 #internal server

@app.route("/post", methods=['PUT'])
@token_required
def edit_post(current_user):
    data = request.json
    id = data.get("id")
    update_data = {}

    if "title" in data:
        update_data["title"] = data["title"]
    if "text" in data:
        update_data["text"] = data["text"]
    if "tags" in data:
        if isinstance(data['tags'],list):
            update_data["tags"] = data["tags"]
        else:
            update_data['tags'] = [data['tags']]
    if "thumbnail" in data:
        if isinstance(data['thumbnail'], list):
            update_data["thumbnail"] = data["thumbnail"]
        else:
            update_data["thumbnail"] = [data["thumbnail"]]

    if not update_data:
        return jsonify({"error": "No valid fields to update"}), 400

    try:
        result = posts_collection.update_one({"_id": ObjectId(id)}, {"$set": update_data})
        if result.modified_count > 0:
            return jsonify({"message": "Post updated successfully"}), 200
        else:
            return jsonify({"error": "No changes made to the post"}), 304
    except Exception as e:
        return jsonify({"error": "Failed to update post"}), 500

@app.route("/post/comments", methods=["POST"])
@token_required
def add_comments(current_user):
    data = request.json
    id = data.get("id")
    comments = data.get("comments")
    if not id or not comments:
        return jsonify({"error": "Missing title or comments in request"}), 400

    try:
        post = posts_collection.find_one({"_id" : ObjectId(id)})
        if post:
            if "comments" not in post:
                collection.update_one({"_id" : ObjectId(id)},{"$set" : {"comments" : []}})
            try:
                result = posts_collection.update_one({"_id" : ObjectId(id)},
                                       {"$push" : {"comments" : comments}})
                return jsonify({"message" : "comments added successfully"})

            except Exception as e:
                return jsonify({"error": "Failed to add comments"}), 500
        else:
            return jsonify({"message": "No comments added"})
    except Exception as e:
        return jsonify({"message" : e})

@app.route("/post/comments", methods=["DELETE"])
@token_required
def delete_comments(current_user):
    data = request.json
    id = data.get("id")
    comments = data.get("comments")
    if not id or not comments:
        return jsonify({"error": "Missing title or comments in request"}), 400

    try:
        post = posts_collection.find_one({"_id" : ObjectId(id)})
        if post:
            try:
                result = posts_collection.update_one({"_id" : ObjectId(id)},
                                       {"$pull" : {"comments" : comments}})
                return jsonify({"message" : "comments deleted successfully"}), 200

            except Exception as e:
                return jsonify({"error": "Failed to deleted comments"}), 500
        else:
            return jsonify({"message": "No comments deleted"}),404
    except Exception as e:
        return jsonify({"message" : e}),500


@app.route("/post/comments", methods=["GET"])
@token_required
def get_comments(current_user):
    data = request.json
    id = data.get("id")
    if not id :
        return jsonify({"error": "missing title or comments in request"}), 400

    try:
        post = posts_collection.find_one({"_id" : ObjectId(id)})
        if post:
            try:
                return jsonify(post['comments']),200
            except Exception as e:
                return jsonify({"error": "Failed to find comments"}), 500
        else:
            return jsonify({"message": "No comments found"}),404
    except Exception as e:
        return jsonify({"message" : str(e)}),500

@app.route("/post/comments", methods=["PUT"])
@token_required
def update_comments(current_user):
    data = request.json
    id = data.get("id")
    pre_comments = data.get("pre_comments")
    new_comments = data.get("new_comments")
    if not id :
        return jsonify({"error": "Missing title or comments in request"}), 400

    try:
        post = posts_collection.find_one({"_id" : ObjectId(id)})
        if post:
            try:
                result = posts_collection.update_one(
                    {"_id" : ObjectId(id), "comments" : pre_comments},
                    {"$set" : {"comments.$" : new_comments}}
                )
                if result.modified_count>0:
                    return jsonify({"message" : "Comments updated successfully"})
                else:
                    return jsonify({"error" : "comments not updated"})
            except Exception as e:
                return jsonify({"error": "Failed to update comments"}), 500
        else:
            return jsonify({"message": "No comments found"}),404
    except Exception as e:
        return jsonify({"message" : e}),500

@app.route("/post/likes", methods=["PUT"])
@token_required
def likes(current_user):
    data = request.json
    id = data.get("id")
    if not id :
        return jsonify({"error": "Missing title in request"}), 400

    try:
        post = posts_collection.find_one({"_id" : ObjectId(id)})
        if post:
            try:
                result = posts_collection.update_one(
                    {"_id" : ObjectId(id)},
                    {"$inc" : {"likes" :1}})
                if result.modified_count>0:
                    return jsonify({"message" : "like added successfully"}),200
                else:
                    return jsonify({"error" : "like not added"}),404
            except Exception as e:
                return jsonify({"error": "Failed to added like"}), 500
        else:
            return jsonify({"message": "No post found"}),404
    except Exception as e:
        return jsonify({"message" : e}),500

@app.route("/post/dislikes", methods=["PUT"])
@token_required
def dislikes(current_user):
    data = request.json
    id = data.get("id")
    if not id :
        return jsonify({"error": "Missing title in request"}), 400

    try:
        post = posts_collection.find_one({"_id" : ObjectId(id)})
        if post:
            try:
                result = posts_collection.update_one(
                    {"_id" : ObjectId(id)},
                    {"$inc" : {"dislikes" :1}})
                if result.modified_count>0:
                    return jsonify({"message" : "dislikes added successfully"}),200
                else:
                    return jsonify({"error" : "dislikes not added"}), 404
            except Exception as e:
                return jsonify({"error": "Failed to added dislikes"}), 500
        else:
            return jsonify({"message": "No post found"}),404
    except Exception as e:
        return jsonify({"message" : e}),500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)