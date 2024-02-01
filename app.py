from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, get_flashed_messages
from flask_caching import Cache
from flask_session import Session
from bokeh.plotting import figure, show
from bokeh.embed import components
from helpers import login_required, convert_to_datetime
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)

#configuring and initalizing the session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#configure cs50 lib to use sqlite

db = SQL("sqlite:///trackr.db")


@app.after_request
def after_request(response):
    #Ensure responses aren't cached
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response



@app.route("/welcome")
def welcome():
    session.clear()
    return render_template("welcome.html")



@app.route("/")
@login_required
def index():

    return redirect("/exercises")


@app.route("/login", methods=["GET", "POST"])
def login():
    get_flashed_messages()
    #forgets any user_id in the session.
    session.clear()

    if request.method == "POST":

        #ensure the boxes have input
        if not request.form.get("username"):
            flash("You have not entered a username.")
            return redirect("/login")

        elif not request.form.get("password"):
            flash("You have not entered a password.")
            return redirect("/login")

        #Query database for username

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        #Ensure username exists and password is correct.

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("invalid username and/or password")
            return redirect("/login")

        #remember which user has logged in
        session["user_id"] = rows[0]["id"]

        #redirect to homepage
        return redirect("/")

    else:
        return render_template("login.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    get_flashed_messages()
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            flash("you have not entered a username.")
            return redirect("/register")

        usernames = db.execute("SELECT username FROM users WHERE username=:username",username=request.form.get("username"))
        if not len(usernames) == 0:
            flash("username already exists.")
            return redirect("/register")

        if not request.form.get("password"):
            flash("you have not entered a password.")
            return redirect("/register")

        if not len(request.form.get("password")) >= 8:
            flash("password must be atleast 8 characters long.")
            return redirect("/register")

        if not request.form.get("confirmation"):
            flash("you must confirm your password.")
            return redirect("/register")

        if not request.form.get("confirmation") == request.form.get("password"):
            flash("your confirmation does not match the password.")
            return redirect("/register")

        hash = generate_password_hash(request.form.get("password"))

        #Insert user into database
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=request.form.get("username"), hash=hash)

        #Get the user dict
        user_dict = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))[0]
        #Create a session
        session["user_id"] = user_dict["id"]

        #Return user to homepage

        return redirect("/")

    #If method is get
    else:
        return render_template("register.html")


@app.route("/exercises", methods=["POST", "GET"])
@login_required
def exercises():

    if request.method == "POST":

        search_ex = request.form.get("search_ex")

        if not search_ex:
            search_ex = ""

        exercise_dicts = db.execute(f"SELECT * FROM exercises WHERE name LIKE '%{search_ex}%'")

        return render_template("exercises.html", exercise_dicts = exercise_dicts)
    else:
        search_ex = ""
        exercise_dicts = db.execute(f"SELECT * FROM exercises WHERE name LIKE '%{search_ex}%'")
        return render_template("exercises.html", exercise_dicts = exercise_dicts)


@app.route("/tracker/<int:exercise_id>", methods=["POST", "GET"])
@login_required
def tracker(exercise_id):
    get_flashed_messages()
    # Here, you can use the 'exercise_id' to fetch the exercise details from the database
    # For example, you can do something like this:
    exercise_history_dict = db.execute("SELECT * FROM exercise_history WHERE exercise_id= :exercise_id AND user_id = :user_id ", exercise_id=exercise_id,user_id=session["user_id"])
    if not exercise_history_dict:
        flash("No data found for this exercise.")
        return redirect("/exercises")


    exercise_name = db.execute("SELECT name FROM exercises WHERE id = :id",id=exercise_id)[0]["name"]
    #We should organize the data into two seperate lists.
    reps_list = []
    weight_list = []
    date_list = []
    for dict in exercise_history_dict:
        reps_list.append(dict["reps"])
        weight_list.append(dict["weight"])
        date_list.append(convert_to_datetime(dict["time"]))

    #Creating the bokeh plot.
    p1 = figure(x_axis_label='Date', y_axis_label='Reps Performed', x_axis_type='datetime')
    p1.line(date_list, reps_list, line_width=2, line_color='#8ade68')

    p2 = figure(x_axis_label='Date', y_axis_label='Weight Lifted', x_axis_type='datetime')
    p2.line(date_list, weight_list, line_width=2, line_color='#8ade68')

    # Convert the plot to components to embed in your Flask template
    script1, div1 = components(p1)
    script2, div2 = components(p2)
    return render_template("tracker.html", script1=script1, div1=div1, script2=script2, div2=div2, exercise_history_dict=exercise_history_dict, exercise_name=exercise_name)


@app.route("/create_workout", methods=["POST","GET"])
@login_required
def create_workout():
    get_flashed_messages()
    exercise_dicts = exercise_dicts = db.execute(f"SELECT * FROM exercises")
    if request.method == "POST":

        #getting the workout id from the sum of all workouts in the platform.
        workout_id = db.execute("SELECT SUM(workout_count) AS total_workout_count FROM users")[0]["total_workout_count"] + 1

        workout_name = request.form.getlist("workout_name")

        if not workout_name:
            workout_name = "Workout #" + str(workout_id)

        exercise_ids = request.form.getlist("exercise_id")

        #insert the name of the workout into workout_name_relation table.
        db.execute("INSERT INTO workout_name_relation (workout_id, workout_name) VALUES (:workout_id, :workout_name)", workout_id=workout_id, workout_name=workout_name)

        #insert into the workout_exercise_relation table.
        for exercise_id in exercise_ids:
            db.execute("INSERT INTO workout_exercise_relation (id, exercise_id) VALUES (:workout_id, :exercise_id)", workout_id=workout_id, exercise_id=exercise_id)
        #Create the relation between the user and the workout.
        db.execute("INSERT INTO user_workout_relation (user_id, workout_id) VALUES (:user_id, :workout_id)", user_id=session["user_id"], workout_id=workout_id)
        #Increment the workout count in the sql table.
        db.execute("UPDATE users SET workout_count = workout_count + 1 WHERE id = :id", id=session["user_id"])


        flash("A new workout is created.")
        return redirect("/workouts")

    else:

        return render_template("create_workout.html", exercise_dicts = exercise_dicts)


@app.route("/workouts", methods=["POST", "GET"])
@login_required
def workouts():
    #we are going to show the exercises by their ids.
    if request.method == "POST":
        return render_template("/")
    else:
        #get the workout ids and names from
        ids_names = []
        id_dict = db.execute("SELECT DISTINCT workout_id FROM user_workout_relation WHERE user_id = :user_id", user_id=session["user_id"])
        #create a 2D array with both the id of the workout and the name of the workout
        for dict in id_dict:
            workout_id = dict["workout_id"]
            workout_name = db.execute("SELECT workout_name FROM workout_name_relation WHERE workout_id = :workout_id", workout_id=workout_id)[0]["workout_name"]
            new_dict = {}
            new_dict["name"] = workout_name
            new_dict["id"] = workout_id
            ids_names.append(new_dict)

        return render_template("workouts.html",ids_names=ids_names)

@app.route("/workout/<int:id>", methods=["GET","POST"])
@login_required
def workout(id):
    get_flashed_messages()
    exercise_ids = db.execute("SELECT * FROM workout_exercise_relation WHERE id = :id", id=id)
    exercises = []
    for dict in exercise_ids:
        exercise = db.execute("SELECT * FROM exercises WHERE id = :id", id=dict["exercise_id"])[0]
        exercises.append(exercise)

    if request.method == "POST":

        for exercise in exercises:
            exercise_id = exercise["id"]
            sets = int(request.form.get(f"sets_{exercise_id}"))
            reps = int(request.form.get(f"reps_{exercise_id}"))
            weight = int(request.form.get(f"weight_{exercise_id}"))
            db.execute("INSERT INTO exercise_history (workout_id, exercise_id, sets, reps, weight, user_id) VALUES (:workout_id, :exercise_id, :sets, :reps, :weight, :user_id)",
                       workout_id=id, exercise_id=exercise_id, sets=sets, reps=reps, weight=weight, user_id=session["user_id"])

            flash("sucessfully finished workout.")
        return render_template("workout.html", workout_id=id, exercises=exercises)
    else:
        return render_template("workout.html", workout_id=id, exercises=exercises)

@app.route("/delete_workout/<int:workout_id>")
def delete_workout(workout_id):

    #this route deletes the workout from the database:
    db.execute("DELETE FROM user_workout_relation WHERE workout_id = :workout_id", workout_id=workout_id)
    db.execute("DELETE FROM workout_exercise_relation WHERE id = :workout_id", workout_id=workout_id)
    db.execute("DELETE FROM workout_name_relation WHERE workout_id = :workout_id",workout_id=workout_id)

    #decrementing each workout id by a number so that ids work properly.
    db.execute("UPDATE user_workout_relation SET workout_id = workout_id - 1 WHERE workout_id > :workout_id", workout_id=workout_id)
    db.execute("UPDATE workout_exercise_relation SET id = id - 1 WHERE id > :workout_id", workout_id=workout_id)
    db.execute("UPDATE workout_name_relation SET workout_id = workout_id - 1 WHERE workout_id > :workout_id", workout_id=workout_id)
    db.execute("UPDATE users SET workout_count = workout_count - 1 WHERE id = :id", id=session["user_id"])

    flash("Successfully deleted workout.")
    return redirect("/workouts")


















