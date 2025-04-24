<!--
parent:
  order: false
-->

<div align="center">
  <h1> skyeye repo </h1>
</div>

<div align="center">
  <a href="https://github.com/SavourDao/skyeye/releases/latest">
    <img alt="Version" src="https://img.shields.io/github/tag/savour-labs/skyeye.svg" />
  </a>
  <a href="https://github.com/SavourDao/skyeye/blob/main/LICENSE">
    <img alt="License: Apache-2.0" src="https://img.shields.io/github/license/savour-labs/skyeye.svg" />
  </a>
</div>

skyeye is the market aggregator of the Savour project, which aggregates the market of centralized and decentralized
transactions. It is written in python and provides grpc interface for upper-layer service access.

**tips**: requirement [python3.12+](https://www.python.org/)

## Install And Local Runing

### 1.create virtual evn

```
git clone git@github.com:roothash-pay/hailstone.git
cd hailstone
python3 -m venv .venv
source venv/bin/activate
```

### 2.install dependencies

```
pip3 install -r requirements.txt
```

### 3.config database

```
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "skyeye",
        "USER": "guoshijiang",
        "PASSWORD": "",
        "HOST": "127.0.0.1",
    },
}
```

Config it according to you environment

### 4.migrate database

```
python3 manage.py makemigrations
python3 manage.py migrate
```

### 5. run dev

```
python3 manage.py runserver
```

### 6. run crawl

```
python3 manage.py broker_crawler crawler_fetch_24tickers
```

## Contribute

### 1.fork repo

fork skyeye to your github

### 2.clone repo

```bash
git@github.com:guoshijiang/skyeye.git
```

### 3.create new branch and commit code

```bash
git branch -C xxx
git checkout xxx

coding

git add .
git commit -m "xxx"
git push origin xxx
```

4.commit PR
Have a pr on your github and submit it to the skyeye repository

5.review
After the skyeye code maintainer has passed the review, the code will be merged into the skyeye repo. At this point,
your PR submission is complete
