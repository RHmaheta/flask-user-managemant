from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

# Initialize Flask app
app = Flask(__name__)

# Test MongoDB connection
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client['project']  # Database name
    users_collection = db['users']  # Collection name
    print("MongoDB connected successfully.")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
    raise

def calculate_age(birthday, target_date=None):
    """Calculate age given a birthday and an optional target date."""
    birthday = datetime.strptime(birthday, "%Y-%m-%d")
    if target_date:
        target_date = datetime.strptime(target_date, "%Y-%m-%d")
    else:
        target_date = datetime.now()
    age = target_date.year - birthday.year - ((target_date.month, target_date.day) < (birthday.month, birthday.day))
    return age

@app.route('/')
def home():
    return "Welcome to the User Management API with MongoDB!", 200

@app.route('/users', methods=['POST'])
def add_user():
    """Add a new user."""
    data = request.get_json()
    if 'name' not in data or 'birthday' not in data:
        return jsonify({"error": "Name and birthday are required."}), 400

    user = {
        "name": data['name'],
        "birthday": data['birthday'],
        "deleted": False
    }
    result = users_collection.insert_one(user)
    user['_id'] = str(result.inserted_id)
    return jsonify(user), 201

@app.route('/users/<string:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update an existing user."""
    try:
        data = request.get_json()
        user = users_collection.find_one({"_id": ObjectId(user_id), "deleted": False})
        if not user:
            return jsonify({"error": "User not found."}), 404

        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'birthday' in data:
            update_data['birthday'] = data['birthday']

        users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        user.update(update_data)

        # Convert ObjectId to string
        user['_id'] = str(user['_id'])
        return jsonify(user), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/users/<string:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Soft-delete a user."""
    try:
        print(f"Attempting to find user with _id: {user_id}")
        user = users_collection.find_one({"_id": ObjectId(user_id), "deleted": False})
        if not user:
            print("User not found or already deleted.")
            return jsonify({"error": "User not found."}), 404

        users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": {"deleted": True}})
        print("User successfully soft-deleted.")
        return jsonify({"message": "User soft-deleted."}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 400

@app.route('/users/<string:user_id>/age', methods=['GET'])
def get_user_age(user_id):
    """Get the age of a user."""
    try:
        print(f"Fetching age for user with _id: {user_id}")
        user = users_collection.find_one({"_id": ObjectId(user_id), "deleted": False})
        if not user:
            print("User not found or already deleted.")
            return jsonify({"error": "User not found."}), 404

        target_date = request.args.get('date')
        age = calculate_age(user['birthday'], target_date)
        print(f"Calculated age: {age}")
        return jsonify({"age": age}), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 400


@app.route('/users/search', methods=['GET'])
def search_users_by_age():
    """Search for users within a specified age range."""
    try:
        min_age = request.args.get('min_age', type=int)
        max_age = request.args.get('max_age', type=int)
        target_date = request.args.get('date') or datetime.now().strftime("%Y-%m-%d")

        result = []
        for user in users_collection.find({"deleted": False}):
            age = calculate_age(user['birthday'], target_date)
            if (min_age is None or age >= min_age) and (max_age is None or age <= max_age):
                user['_id'] = str(user['_id'])
                result.append(user)

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
