from django.shortcuts import render, redirect, get_object_or_404
from .models import Movie, Rating
from django.contrib.auth.decorators import login_required
from .forms import RatingForm
from random import shuffle
import csv
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import io
import boto3
# Create your views here.


def home(request):
    # 로그인 여부 판단
    if not request.user.is_authenticated:
        return redirect("/sign-in")

    return redirect('/main')


# 추천 시스템 api
def show_movie(request):
    # s3_client = boto3.client('s3')
    # s3_rating_object = s3_client.get_object(Bucket="green-cinema", Key="data/ratings (1).csv")
    # s3_movie_object = s3_client.get_object(Bucket="green-cinema", Key="data/movies (1).csv")

    ratings = pd.read_csv('static/data/ratings (1).csv')
    movies = pd.read_csv('static/data/movies (1).csv')

    pd.set_option('display.max_columns', 10)
    pd.set_option('display.width', 300)
    movie_ratings = pd.merge(ratings, movies, on='movieId')
    title_user = movie_ratings.pivot_table('rating', index='userId', columns='movieId')

    title_user = title_user.fillna(0)
    user_based_collab = cosine_similarity(title_user, title_user)
    user_based_collab = pd.DataFrame(user_based_collab, index=title_user.index, columns=title_user.index)
    user = user_based_collab[request.user.id].sort_values(ascending=False)[:10].index[1]
    result = title_user.query(f"userId == {user}").sort_values(ascending=False, by=user, axis=1).columns
    result_list = list(result)
    return result_list[:10]


def main_view(request):
    # 사용자가 있는지 없는지 판단
    if request.method == 'GET':
        user = request.user.is_authenticated
        if user:
            # Movie.objects.all() : 무비 모델에 있는 모든 오브젝트를 불러옴
            all_movie = list(Movie.objects.all())
            shuffle(all_movie)
            my_rating = Rating.objects.filter(user_id=request.user.id).exists()
            # print(my_rating)
            if my_rating:
                # 추천 시스템 api 호출
                results = show_movie(request)
                suggestion_list = []
                for result in results:
                    movie = Movie.objects.get(id=result)
                    suggestion_list.append(movie)

                return render(request, 'movie/main.html', {'movie': all_movie[:50], 'suggestion_list': suggestion_list[:6]})

            else:
                return render(request, 'movie/main.html', {'movie': all_movie[:50]})
            # test.html 에서 데이터 response 확인 완료
            # return render(request, 'movie/test.html', {'movie': movie_shuffle[:50]})
        else:
            return redirect(('/sign-up'))
    else:
        return redirect('/')


def genre_view(request):
    if request.method == 'GET':
        user = request.user.is_authenticated
        if user:
            # 장르 list
            genre_list = ['Adventure', 'Comedy', 'Action', 'Drama', 'Crime', 'Children', 'Mystery', 'Animation',
                          'Documentary', 'Thriller', 'Horror', 'Fantasy', 'Western', 'Film-Noir', 'Romance', 'Sci-Fi',
                          'Musical', 'War', 'IMAX']
            movie_genre_dict_list = []
            for gen in genre_list:
                # Movie 모델의 오브젝트를 가져 오는데 genre 컬럼 안에 gen이 포함되어 있는 경우만 필터링 해서 가져옴
                # type : list 안에 object / [object, object]
                movie_list = list(Movie.objects.filter(genre__contains=gen))
                shuffle(movie_list)
                movie_shuffle = movie_list
                # type : 딕셔너리에 gen를 키로 가지고 movie_list를 밸류로 가지는 객체 추가
                movie_genre_dict_list.append({gen: movie_shuffle[:6]})
            return render(request, 'movie/genre.html', {'genre_list': genre_list, 'movie_genre_dict_list': movie_genre_dict_list})
            # test.html에서 데이터 response 확인 완료
            # return render(request, 'movie/test.html', {'genre_list': genre_list, 'movie_genre_dict_list': movie_genre_dict_list})
        else:
            return redirect(('/sign-up'))
    else:
        return redirect('/')

# rating 존재 확인 함수 / rating테이블에서 user_id, movie_id가 일치하는 데이터를 리턴, 데이터가 없다면 오류 발생 '0'을 리턴


def existence_rating(request, id):
    try:
        my_rating = get_object_or_404(
            Rating, user_id=request.user.id, movie_id=id)
        return my_rating
    except:
        return '0'


# contents.html(콘텐츠 상세파일) 호출 함수
def contents_view(request, id):
    # 영화 아이디로 Movie 테이블 조회
    contents_movie = Movie.objects.get(id=id)
    check_exist = existence_rating(request, id)
    rating_data = Rating.objects.filter(movie_id=id)
    if check_exist == '0':
        form = RatingForm()
        return render(request, 'movie/contents.html',
                      {'contents_movie': contents_movie, 'form': form, "check_exist": check_exist, "rating_data": rating_data})
        # return render(request, 'movie/contents_test.html', {'contents_movie': contents_movie, 'form': form, 'ms': '0'})
    else:
        form = RatingForm(instance=check_exist)
        return render(request, 'movie/contents.html',
                      {'contents_movie': contents_movie, 'form': form, 'check_exist': check_exist, "rating_data": rating_data})
        # return render(request, 'movie/contents_test.html', {'contents_movie': contents_movie, 'form': form, 'ms': '1'})


# rating 생성 함수
@login_required
def rating_create(request, id):
    if request.method == 'POST':  # POST 방식으로 요청이 들어왔을 때
        form = RatingForm(request.POST)  # 입력된 내용들을 form이라는 변수에 저장
        if form.is_valid():  # form이 유효하다면(models.py에서 정의한 필드에 적합하다면)
            # form 데이터를 가져온다. (commit=False : 바로 저장되는 기능을 홀딩)
            rating = form.save(commit=False)
            rating.user_id = request.user
            rating.movie_id = Movie.objects.get(id=id)
            rating.save()  # form 데이터를 DB에 저장한다.
            f = open('static/data/ratings (1).csv', 'a', newline='')
            wr = csv.writer(f)
            wr.writerow([request.user.id, rating.movie_id.id, rating.rating])
            f.close()
            d = pd.read_csv('static/data/ratings (1).csv', sep=",")
            d = d.drop_duplicates(['userId', 'movieId'], keep='last')
            d.to_csv('static/data/ratings (1).csv', index=False)
            # s3_client = boto3.client('s3')
            # s3_object = s3_client.get_object(Bucket="green-cinema", Key="data/ratings (1).csv")
            # # read the file
            # df = pd.read_csv(s3_object['Body'])
            # new = pd.DataFrame(
            #     {"userId": [request.user.id], "movieId": [rating.movie_id.id], "rating": [rating.rating]})
            # concat = pd.concat((df, new)).reset_index(drop=True)
            # concat = concat.drop_duplicates(['userId', 'movieId'], keep='last')
            # csv_buffer = io.StringIO()
            # concat.to_csv(csv_buffer, index=False)
            # s3_client.put_object(Body=csv_buffer.getvalue(), Bucket='green-cinema', Key='data/ratings (1).csv')
            return redirect('/contents/' + str(id))
        else:
            return redirect('/contents/' + str(id))
    else:  # GET 방식으로 요청이 들어왔을 때
        return redirect('/contents/' + str(id))

# rating 업데이트 함수


@login_required
def rating_update(request, id):
    if request.method == 'POST':
        # rating 테이블에서 user_id, movie_id 일치하는 데이터 가져옴 / update함수는 데이터가 있는 경우에만 호출 되기 때문에 오류뜨면 안됨 / but 나중에 오류처리는 해야될듯?
        my_rating = get_object_or_404(
            Rating, user_id=request.user.id, movie_id=id)
        # form 변수에 request.POST내용을 가져와서 이미 있는 Rating클래스의 인스턴스에(my_rating) 업데이트
        form = RatingForm(request.POST, instance=my_rating)

        if form.is_valid():
            # form 데이터를 가져온다. (commit=False : 바로 저장되는 기능을 홀딩) // 사실 여기서는 바로 저장해도 문제없을듯
            rating = form.save(commit=False)
            rating.save()  # form 데이터를 DB에 저장한다.
            f = open('static/data/ratings (1).csv', 'a', newline='')
            wr = csv.writer(f)
            wr.writerow([request.user.id, rating.movie_id.id, rating.rating])
            f.close()
            d = pd.read_csv('static/data/ratings (1).csv', sep=",")
            d = d.drop_duplicates(['userId', 'movieId'], keep='last')
            d.to_csv('static/data/ratings (1).csv', index=False)
            # s3_client = boto3.client('s3')
            # s3_object = s3_client.get_object(Bucket="green-cinema", Key="data/ratings (1).csv")
            # # read the file
            # df = pd.read_csv(s3_object['Body'])
            # new = pd.DataFrame({"userId": [request.user.id], "movieId": [rating.movie_id.id], "rating": [rating.rating]})
            # concat = pd.concat((df, new)).reset_index(drop=True)
            # concat = concat.drop_duplicates(['userId', 'movieId'], keep='last')
            # csv_buffer = io.StringIO()
            # concat.to_csv(csv_buffer, index=False)
            # s3_client.put_object(Body=csv_buffer.getvalue(), Bucket='green-cinema', Key='data/ratings (1).csv')
            return redirect('/contents/' + str(id))
        else:
            return redirect('/contents/' + str(id))
    else:  # GET 방식으로 요청이 들어왔을 때
        return redirect('/contents/' + str(id))



