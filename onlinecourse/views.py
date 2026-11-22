from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic

from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate

from .models import Course, Enrollment, Question, Choice, Submission

import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)


# -------------------------------
# USER REGISTRATION
# -------------------------------

def registration_request(request):
    context = {}

    if request.method == 'GET':
        return render(
            request,
            'onlinecourse/user_registration_bootstrap.html',
            context
        )

    elif request.method == 'POST':

        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']

        # Check whether username already exists
        user_exist = User.objects.filter(username=username).exists()

        if not user_exist:

            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                password=password
            )

            login(request, user)

            return redirect("onlinecourse:index")

        else:
            context['message'] = "User already exists."

            return render(
                request,
                'onlinecourse/user_registration_bootstrap.html',
                context
            )


# -------------------------------
# USER LOGIN
# -------------------------------

def login_request(request):

    context = {}

    if request.method == "POST":

        username = request.POST['username']
        password = request.POST['psw']

        user = authenticate(
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            return redirect('onlinecourse:index')

        else:

            context['message'] = "Invalid username or password."

            return render(
                request,
                'onlinecourse/user_login_bootstrap.html',
                context
            )

    else:

        return render(
            request,
            'onlinecourse/user_login_bootstrap.html',
            context
        )


# -------------------------------
# USER LOGOUT
# -------------------------------

def logout_request(request):

    logout(request)

    return redirect('onlinecourse:index')


# -------------------------------
# CHECK ENROLLMENT
# -------------------------------

def check_if_enrolled(user, course):

    is_enrolled = False

    if user.is_authenticated:

        num_results = Enrollment.objects.filter(
            user=user,
            course=course
        ).count()

        if num_results > 0:
            is_enrolled = True

    return is_enrolled


# -------------------------------
# COURSE LIST VIEW
# -------------------------------

class CourseListView(generic.ListView):

    template_name = 'onlinecourse/course_list_bootstrap.html'

    context_object_name = 'course_list'

    def get_queryset(self):

        user = self.request.user

        courses = Course.objects.order_by(
            '-total_enrollment'
        )[:10]

        for course in courses:

            if user.is_authenticated:

                course.is_enrolled = check_if_enrolled(
                    user,
                    course
                )

        return courses


# -------------------------------
# COURSE DETAIL VIEW
# -------------------------------

class CourseDetailView(generic.DetailView):

    model = Course

    template_name = 'onlinecourse/course_detail_bootstrap.html'


# -------------------------------
# ENROLL IN COURSE
# -------------------------------

def enroll(request, course_id):

    course = get_object_or_404(
        Course,
        pk=course_id
    )

    user = request.user

    is_enrolled = check_if_enrolled(
        user,
        course
    )

    if not is_enrolled and user.is_authenticated:

        Enrollment.objects.create(
            user=user,
            course=course,
            mode='honor'
        )

        course.total_enrollment += 1

        course.save()

    return HttpResponseRedirect(
        reverse(
            viewname='onlinecourse:course_details',
            args=(course.id,)
        )
    )


# -------------------------------
# EXTRACT ANSWERS FROM EXAM FORM
# -------------------------------

def extract_answers(request):

    submitted_answers = []

    for key in request.POST:

        if key.startswith('choice'):

            value = request.POST[key]

            choice_id = int(value)

            submitted_answers.append(choice_id)

    return submitted_answers


# -------------------------------
# SHOW EXAM RESULT
# -------------------------------

def show_exam_result(request, course_id, submission_id):

    context = {}

    # Get course
    course = get_object_or_404(
        Course,
        pk=course_id
    )

    # Get submission and verify that it belongs to the logged-in user
    submission = get_object_or_404(
        Submission,
        id=submission_id,
        enrollment__user=request.user,
        enrollment__course=course
    )

    # Get all selected choices
    choices = submission.choices.all()

    # Initialize total score
    total_score = 0

    # Store question-wise results
    question_results = []

    # Get all questions of this course
    questions = course.question_set.all()

    for question in questions:

        # Get correct choices for this question
        correct_choices = question.choice_set.filter(
            is_correct=True
        )

        # Get selected choices for this question
        selected_choices = choices.filter(
            question=question
        )

        # Check whether selected choices exactly match correct choices
        is_correct = (
            set(correct_choices) == set(selected_choices)
            and correct_choices.exists()
        )

        # Calculate marks
        if is_correct:

            total_score += question.grade

        # Store question result
        question_results.append({

            'question': question,

            'selected_choices': selected_choices,

            'correct_choices': correct_choices,

            'is_correct': is_correct,

            'grade': question.grade if is_correct else 0

        })

    # Calculate total possible marks
    total_marks = sum(
        question.grade for question in questions
    )

    # Check whether learner passed
    # Assuming passing marks are 50% of total marks
    passing_marks = total_marks * 0.5

    passed = total_score >= passing_marks

    # Add information to context
    context['course'] = course

    context['submission'] = submission

    context['grade'] = total_score

    context['total_score'] = total_score

    context['total_marks'] = total_marks

    context['passing_marks'] = passing_marks

    context['passed'] = passed

    context['choices'] = choices

    context['question_results'] = question_results

    # Render result page
    return render(
        request,
        'onlinecourse/exam_result_bootstrap.html',
        context
    )
