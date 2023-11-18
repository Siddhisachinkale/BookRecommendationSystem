from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import pickle
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, session, current_app
from flask_sqlalchemy import SQLAlchemy


popular_df = pickle.load(open('popular.pkl','rb'))
pt = pickle.load(open('pt.pkl','rb'))
books = pickle.load(open('books.pkl','rb'))
similarity_scores = pickle.load(open('similarity_scores.pkl','rb'))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:root123@localhost:3306/bookdb'

  # Use an actual database like PostgreSQL in production
app.secret_key = 'your_secret_key'  # Replace with a strong secret key in production

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(13), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500), nullable=False)

popular_df = pickle.load(open('popular.pkl', 'rb'))
pt = pickle.load(open('pt.pkl', 'rb'))
books = pickle.load(open('books.pkl', 'rb'))
similarity_scores = pickle.load(open('similarity_scores.pkl', 'rb'))
popular_df['Image-URL-M'] = popular_df['Image-URL-M'].str.replace("http://", "https://")
with open('books.pkl', 'rb') as file:
    book_data = pickle.load(file)
@app.route('/')
def index():

     return render_template('index.html')

@app.route('/popular')
def popular():
    return render_template('popular.html',
        book_name=list(popular_df['Book-Title'].values),
        author=list(popular_df['Book-Author'].values),
        image=list(popular_df['Image-URL-M'].values),
        votes=list(popular_df['num_ratings'].values),
        rating=list(popular_df['avg_ratings'].values)
    )




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session['user_id'] = user.id
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))



@app.route('/recommend')
def recommend_ui():
    return render_template('recommend.html')

@app.route('/recommend_books',methods=['post'])
def recommend():
    user_input = request.form.get('user_input')
    index = np.where(pt.index == user_input)[0][0]
    similar_items = sorted(list(enumerate(similarity_scores[index])), key=lambda x: x[1], reverse=True)[1:5]

    data = []
    for i in similar_items:
        item = []
        temp_df = books[books['Book-Title'] == pt.index[i[0]]]
        item.extend(list(temp_df.drop_duplicates('Book-Title')['Book-Title'].values))
        item.extend(list(temp_df.drop_duplicates('Book-Title')['Book-Author'].values))
        item.extend(list(temp_df.drop_duplicates('Book-Title')['Image-URL-M'].values))

        data.append(item)

    print(data)

    return render_template('recommend.html',data=data)

# In your search route
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form['query'].lower()
        print("Query:", query)  # Add this line for debugging
        print("book_data:", book_data)  # Add this line for debugging
        results = book_data[book_data['Book-Title'].str.lower().str.contains(query)].to_dict(orient='records')
        print("Results:", results)  # Add this line for debugging
        return render_template('search_results.html', results=results)
    return render_template('search.html')


@app.route('/book/<isbn>')
def book_details(isbn):
    # Use Pandas to filter the DataFrame for the book with the given ISBN
    book = book_data[book_data['ISBN'] == isbn].to_dict(orient='records')

    if book:
        # Specify the fields you want to display
        fields_to_display = ['ISBN', 'Book-Title', 'Book-Author', 'Year-Of-Publication', 'Publisher', 'Image-URL-M']
        book_details = {field: book[0][field] for field in fields_to_display}
        return render_template('search_details.html', book=book_details)
    else:
        return render_template('book_not_found.html')



# Add this route for submitting reviews.
@app.route('/submit_review/<isbn>', methods=['POST'])
def submit_review(isbn):
    if 'user_id' in session:
        username = User.query.get(session['user_id']).username
        rating = int(request.form.get('rating'))
        comment = request.form.get('review')

        # Create a new review and add it to the database
        new_review = Review(isbn=isbn, username=username, rating=rating, comment=comment)
        db.session.add(new_review)
        db.session.commit()

        # Redirect back to the book details page with a success message
        return redirect(url_for('book_details', isbn=isbn, review_success=True))
    else:
        return redirect(url_for('login'))


@app.route('/book_reviews/<isbn>')
def book_reviews(isbn):
    # Fetch the book title from the pickle file
    with open('books.pkl', 'rb') as file:
        book_data = pickle.load(file)

    # Try to find the book title based on the ISBN from the pickle data
    book = book_data[book_data['ISBN'] == isbn]
    book_title = book['Book-Title'].values[0] if not book.empty else "Title Not Found"

    # Query the database to retrieve all reviews for the given ISBN
    reviews = Review.query.filter_by(isbn=isbn).all()

    return render_template('book_reviews.html', reviews=reviews, book_title=book_title)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)