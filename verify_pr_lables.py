#!/usr/bin/env python3

import os
import sys
import re
from github import Github

def get_env_var(env_var_name, echo_value=False):
    """Try to get the value from a environmental variable.

    If the values is 'None', then a ValueError exception will
    be thrown.

    Args:
        env_var_name (string): The name of the environmental variable.
        echo_value (bool): Print the resulting value

    Returns:
        string: the value from the environmental variable.
    """
    value=os.environ.get(env_var_name)

    if value == None:
        raise ValueError(f'The environmental variable {env_var_name} is empty!')

    if echo_value:
        print(f"{env_var_name} = {value}")

    return value

# Check if the number of input arguments is correct
if len(sys.argv) != 3:
    raise ValueError('Invalid number of arguments!')

# Get the GitHub token
token=sys.argv[1]

# Get the list of valid labels
valid_labels=sys.argv[2]
print(f'Valid labels are: {valid_labels}')

# Get needed values from the environmental variables
repo_name=get_env_var('GITHUB_REPOSITORY')
github_ref=get_env_var('GITHUB_REF')

# Create a repository object, using the GitHub token
repo = Github(token).get_repo(repo_name)

# Try to extract the pull request number from the GitHub reference.
try:
    pr_number=int(re.search('refs/pull/([0-9]+)/merge', github_ref).group(1))
    print(f'Pull request number: {pr_number}')
except AttributeError:
    raise ValueError(f'The Pull request number could not be extracted from the GITHUB_REF = {github_ref}')

# Create a pull request object
pr = repo.get_pull(pr_number)

# Get the pull request labels
pr_labels = pr.get_labels()

# Get the list of reviews
pr_reviews = pr.get_reviews()

# This is a list of valid label found in the pull request
pr_valid_labels = []

# Check which of the label in the pull request, are in the
# list of valid labels
for label in pr_labels:
    if label.name in valid_labels:
        pr_valid_labels.append(label.name)

# Look for the last review done by this module
was_approved = None
for review in pr_reviews.reversed:
    if review.user.login == 'github-actions[bot]':
        print(f'Last review found: status = {review.state}')
        if review.state == 'APPROVED':
            was_approved = True
        elif review.state == 'REQUEST_CHANGES':
            was_approved = False

        # Break this loop after the last review is found.
        # If no review was done, 'was_approved' will remain
        # as 'None'.
        break

# Check if there were at least one valid label
# Note: In both cases we exit without an error code and let the check to succeed. This is because GitHub
# workflow will create different checks for different trigger conditions. So, adding a missing label won't
# clear the initial failed check during the PR creation, for example.
# Instead, we will create a pull request review, marked with 'REQUEST_CHANGES' when no valid label was found.
# This will prevent merging the pull request until a valid label is added, which will trigger this check again
# and will create a new pull request review, but in this case marked as 'APPROVE'

print(f'was_approved = {was_approved}')

if len(pr_valid_labels):
    # If there were valid labels, create a pull request review, approving it
    print(f'Success! This pull request contains the following valid labels: {pr_valid_labels}')

    # If the last review done was approved, then don't do it again
    if was_approved == True:
        print(f'The last review was approved, so it is not going to be approved again')
    else:
        pr.create_review(event = 'APPROVE')
else:
    # If there were not valid labels, then create a pull request review, requesting changes
    print(f'Error! This pull request does not contain any of the valid labels: {valid_labels}')

    # If the last review done was not approved, then don't do it again
    if was_approved == False:
        print(f'The last review requested changes, so it is not going to request changes again')
    else:
        pr.create_review(body = 'This pull request does not contain a valid label. '
                                f'Please add one of the following labels: `{valid_labels}`',
                         event = 'REQUEST_CHANGES')
