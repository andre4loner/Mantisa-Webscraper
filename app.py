
from bson.objectid import ObjectId
from flask import Flask, g, request, redirect, url_for, render_template, session
from flask_pymongo import PyMongo
import yaml, bcrypt, json, bson, certifi

# for scraping
from bs4 import BeautifulSoup
import requests, operator


app = Flask(__name__)
cred = yaml.load(open('cred.yaml'))
app.config['MONGO_URI'] = cred['mongo_uri']
mongo = PyMongo(app, tlsCAFile=certifi.where())
app.secret_key = 'mysecretkey'

users_collection = mongo.db.users
products_collection = mongo.db.products
wish_lists_collection = mongo.db.wish_lists
deleted_lists_collection = mongo.db.deleted_lists

@app.before_request
def before_request():
  if 'user_id' in session:
    current_user = users_collection.find_one({
      "_id": bson.ObjectId(session["user_id"])
    })
    # print(session["user_id"])
    g.user = current_user
    # print(g.user)
    print(g.user['name'])


@app.route('/')
def home():
  current_user = users_collection.find_one({
      "name": "beibi"
    })
  # print(current_user)
  # print(current_user['_id'])
  # print(str(ObjectId(current_user['_id'])))

  if 'user_id' in session:
    return render_template('home.html')
  else:
    return render_template('index.html')


# check
@app.route('/login', methods=['GET', 'POST'])
def login():
  if 'user_id' in session:
    return redirect(url_for('home'))

  if request.method == 'POST':
    session.pop('user_id', None)
    not_found_message = "Email or password is incorrect, please try again."
    user = users_collection.find_one({
      "email": request.form["email"]
    })
    if (user == None):
      return render_template('login.html', message=not_found_message)
    else:
      if (bcrypt.checkpw(request.form["password"].encode("utf-8"), user['password'])):
        session['user_id'] = str(ObjectId(user['_id']))
        return redirect(url_for('home'))
      else:
        return render_template('login.html', message=not_found_message)

  return render_template('login.html', message="")


# check
@app.route('/signup', methods=['GET', 'POST'])
def signup():
  if 'user_id' in session:
    return redirect(url_for('home'))
    
  if request.method == 'POST':
    hashed_password = bcrypt.hashpw(request.form["password"].encode("utf-8"), bcrypt.gensalt(10))

    users_collection.insert_one({
      "name": request.form["name"],
      "email": request.form["email"],
      "password": hashed_password,
      "wish_list": [],
      "deleted_list": [],
    })
    registered_user = users_collection.find_one({
      "email": request.form["email"]
    }).id
    session['user_id'] = registered_user._id
    return redirect(url_for('home'))

  return render_template('signup.html')


# check
@app.route('/logout')
def logout():
  session.pop('user_id', None)
  return redirect(url_for('home'))



@app.route(f'/search')
def results():
  if 'user_id' not in session:
    return redirect(url_for('home'))

  products_jumia = []
  products_konga = []

  def spider_jumia(i_name_raw, category_raw, max_pages):  
    page = 1
    i_name = i_name_raw.replace(' ', '+')
    category = category_raw.replace(' ', '-')
    count = 1
    while (page <= max_pages):
      headers = {'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36'}
      url = f'https://www.jumia.com.ng/{category}/?q={i_name}&page={page}'
      html = requests.get(url, headers).text
      soup = BeautifulSoup(html, 'html.parser')
      wrappers = soup.find_all('article', class_='prd _fb col c-prd')

      for w in wrappers:
        item = w.find('a', attrs={"data-category": ["Phones & Tablets/Mobile Phones/Smartphones/iOS Phones", "Phones & Tablets/Mobile Phones/Smartphones/Android Phones"]})

        if ((item != None) and (len(item.find('div', class_='prc').text.strip()) <= 9)):
          if(i_name_raw.lower() in item.find('h3', class_='name').text.strip().lower()):
            name_ = item.find('h3', class_='name').text.strip()
            if (len(name_) > 55):
              name = f'{name_[:55]}   ...{name_[-15::]}'
            else:
              name = name_
            price_raw = item.find('div', class_='prc').text.strip()
            price_no_currency = price_raw[2:]
            price_int_parts = price_no_currency.split(',')
            price = (int(price_int_parts[0])*1000) + int(price_int_parts[1])
            img = item.find('img').get('data-src')
            link = "https://jumia.com.ng" + item.get('href')
            marketplace_logo = "https://logosarchive.com/wp-content/uploads/2021/05/jumia-seeklogo.com_.png"
            product_jumia = [name, price, img, link, marketplace_logo]
            # print(product_jumia[0],'\n',product_jumia[1],'\n',product_jumia[3], "\n\n")
            products_jumia.append(product_jumia)
            count += 1
      page += 1

  def spider_konga(i_name_raw):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'content-type': 'application/json',
        'x-app-source': 'kongavthree',
        'x-app-version': '2.0',
        'Origin': 'https://www.konga.com',
        'Connection': 'keep-alive',
        'Referer': 'https://www.konga.com/',
        'TE': 'Trailers',
    }

    data = '{"query":"{\\n searchByStore (search_term: [], numericFilters: [], sortBy: \\"\\", query: \\"' + i_name_raw + '\\", paginate: {page: 0, limit: 30}, store_id: 1) {\\npagination {limit,page,total},products {image_thumbnail,name,price,special_price,url_key,categories {name,url_key},seller {id,name}}\\n }\\n }\\n "}'

    response = requests.post('https://api.konga.com/v1/graphql', headers=headers, data=data)
    content = json.loads(response.content)
    content_products = content['data']['searchByStore']['products']

    # print(response, "\n\n")
    count = 1
    for p in content_products:
      if ((p['categories'] != None) and (p['categories'][2] != None)):
        if (p['categories'][2]['name'].lower() == 'smartphones'):
          name = p['name']
          price = p['special_price']
          category = p['categories'][2]['name']
          img = 'https://www-konga-com-res.cloudinary.com/w_850,f_auto,fl_lossy,dpr_auto,q_auto/media/catalog/product' + p['image_thumbnail']
          link = 'https://www.konga.com/product/' + p['url_key']
          marketplace_logo = 'https://www.konga.com/static/meta-logo.png'
          product_konga = [name, price, img, link, marketplace_logo]
          products_konga.append(product_konga)
          print(f'name -> {name}')
          print(f'price -> {price}')
          print(f'category -> {category}')
          print(f'img -> {img}')
          print(f'link -> {link}')
          
          count += 1

  query = request.args.get('q')
  options = request.args.get('options')

  spider_konga(query)
  spider_jumia(query, options, 2)

  products_unsorted = products_jumia + products_konga
  products = sorted(products_unsorted, key=operator.itemgetter(1))

  return render_template('results.html', products=products, query=query)


@app.route('/profile', methods=['GET', 'POST'])
def profile():
  if 'user_id' not in session:
    return redirect(url_for('home'))

  if request.method == 'POST':
    cur = mysql.connection.cursor()
    result = cur.execute("select * from user")
    last_id = 1
    if result > 0:
      list = cur.fetchall()
      for item in list:
        last_id = item[0] + 1
    cur.close()
    id = g.user[0]
    cur2 = mysql.connection.cursor()
    name = request.form["name"]
    surname = request.form["surname"]
    email = request.form["email"]
    password = request.form["password"]
    cur2.execute(f"update user set name = %s, surname = %s, email = %s, password = %s where id = {id}", (name, surname, email, password,))
    # f"update user set password = '{password}
    # cur2.execute("insert into user values (%s, %s, %s, %s, %s)", (last_id, name, surname, email, password,))
    mysql.connection.commit()
    cur2.close()
    session['user_id'] = last_id
    return redirect(url_for('login'))

  return render_template('profile.html')


@app.route('/lists')
def lists():
  if 'user_id' not in session:
    return redirect(url_for('home'))

  return render_template('lists.html')


@app.route('/wish')
def wish():
  if 'user_id' not in session:
    return redirect(url_for('home'))

  wish_list = users_collection.find_one({
    "_id": bson.ObjectId(session["user_id"])
  })['wish_list']

  return render_template('wish.html', wish_list=wish_list)


@app.route('/deleted')
def deleted():
  if 'user_id' not in session:
    return redirect(url_for('home'))

  deleted_list = users_collection.find_one({
    "_id": bson.ObjectId(session["user_id"])
  })['deleted_list']

  return render_template('wish.html', deleted_list=deleted_list)


if __name__ == '__main__':
  app.run(debug=True)
