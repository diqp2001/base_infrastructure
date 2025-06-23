#✅ Typical Workflow Example
"""Start a new feature:

bash
Copier
Modifier
if doesnt exist git checkout -b develop
git checkout develop
git checkout -b feature/my-new-feature
When done:

bash
Copier
Modifier
git checkout develop
git merge feature/my-new-feature
git branch -d feature/my-new-feature
When ready to release:

bash
Copier
Modifier
git checkout -b release/1.0 develop
# bump version, fix bugs...
git checkout main
git merge release/1.0
git tag -a v1.0 -m "Release 1.0"
git checkout develop
git merge release/1.0
git branch -d release/1.0

git branch         # shows all local branches
git branch -r      # shows remote branches"""