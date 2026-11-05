# Hosting the project page

The same static files work from a domain root or a repository subpath. Every runtime asset reference
is relative. Build the export first:

```bash
python3 scripts/package_site.py --zip dist/latent-rl-prior-site.zip
```

## Which deployment to use

- **Public project page (current version):** GitHub Pages, described below. Pushing to `main`
  deploys automatically.
- **Anonymous review snapshot:** the anonymous page is kept in
  `.local-backups/2026-11-05-anonymous-version/`. If a reviewer link is needed, host only that
  snapshot on Anonymous GitHub or CloudFront (sections below). Never upload the public version there.

## First-time GitHub setup

This folder is not yet a Git repository. From this folder:

```bash
git init -b main
git add .
git commit -m "Initial project page"
```

Create an empty repository on github.com (no README or license, so the first push does not conflict),
then push:

```bash
git remote add origin git@github.com:<account>/<repository>.git
git push -u origin main
```

`.gitignore` already excludes `dist/`, `private/`, and `.local-backups/`. Everything else, including
`docs/`, `scripts/`, and `CLAUDE.md`, is visible to anyone who can read the repository; only `dist/site`
is published as the website.

## Anonymous GitHub

1. Put this standalone website in a new GitHub repository. Do not upload the research workspace or
   its history. Use a private source repository if your account and the anonymous-hosting service
   support access to it.
2. Sign in to [Anonymous GitHub](https://anonymous.4open.science/) and connect the website repository.
   Configure terms to anonymize, including author names, usernames, and institutions. Keep that
   identity list in the service configuration, not in the website repository.
3. Configure the service's website/Pages support, with the branch containing this page and `/` as the
   source directory. Use the website URL the service actually generates. The desired shape is:

   ```text
   https://anonymous.4open.science/r/<generated-id>/index.html
   ```

4. Check the generated URL in a signed-out/private browser: load the figures, select all three tasks,
   play videos, open the PDF, and inspect all links. If the service serves HTML as source or blocks
   scripts/video, use the CloudFront export below instead.
5. Keep the anonymous artifact available throughout the review period. Use the generated website
   URL in the paper, not the source GitHub repository URL.

The public service returned HTTP 403 to the automated reader used during preparation, so deployment
on that service has **not** been verified. Its upstream implementation exposes website source
settings (`page` and `pageSource`); the live UI and account requirements may differ. See the
[service's own README](https://github.com/tdurieux/anonymous_github#usage).

## CloudFront with a private S3 origin

`deployment/cloudfront.yml` creates a private S3 bucket, a CloudFront distribution with origin access
control, HTTPS redirection, and response headers. S3 Block Public Access stays enabled. Only the
CloudFront distribution can read objects from the bucket. The website is intentionally public through
CloudFront.

Use an AWS account and profile authorized to host this paper. Run these creation commands only
when setting up a new deployment. For the existing deployment, use its recorded stack outputs
and the update commands below.

```bash
aws cloudformation deploy \
  --template-file deployment/cloudfront.yml \
  --stack-name latent-rl-prior-site

aws cloudformation describe-stacks \
  --stack-name latent-rl-prior-site \
  --query 'Stacks[0].Outputs'
```

Copy the `BucketName`, `DistributionId`, and `WebsiteURL` outputs. Upload only the exported site:

```bash
aws s3 sync dist/site/ s3://BUCKET_NAME/ \
  --exclude '.site-export' \
  --cache-control 'public,max-age=3600'
```

For updates, upload the new export and invalidate the old cache:

```bash
aws cloudfront create-invalidation \
  --distribution-id DISTRIBUTION_ID \
  --paths '/*'
```

The generated `WebsiteURL` is an anonymous-looking `https://d….cloudfront.net/` hostname. Use that
hostname directly instead of an author or institution domain. Confirm the page and its assets return
successful responses anonymously, that the PDF downloads, and that videos play and seek. An
anonymous request directly to the S3 origin should remain denied.

Do not upload Git history, source workspace files, private notes, or the entire repository to S3.
The `dist/site` allowlist keeps them out. The distribution template retains the bucket if the stack is
deleted, to avoid deleting the uploaded paper accidentally.

Reference: [CloudFront origin access control for S3](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html).

## GitHub Pages

This option is useful for the public project page after review. An ordinary GitHub Pages hostname
contains the account name, so it should not be the paper's anonymous link.

1. Push this standalone repository to the intended account (see “First-time GitHub setup”).
   GitHub Pages on GitHub Free requires a public repository.
2. In **Settings → Pages**, set the publishing source to **GitHub Actions**.
3. In **Actions**, open **Publish project page** and click **Run workflow** for the first deployment.
4. Use the deployment URL reported by the workflow, normally
   `https://<account>.github.io/<repository>/`. Later pushes to `main` redeploy automatically;
   the workflow fails, and nothing is published, if validation fails (for example, a leftover
   `TODO-` placeholder).

The workflow validates the site and uploads only `dist/site`, never the entire source repository.
See [GitHub's custom Pages workflow guide](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## Anonymity checks before linking the paper

The page already has anonymous authorship, local assets, stripped PDF/media metadata, and no tracking
or author links. `noindex` and `robots.txt` discourage indexing; they are not access controls or a
guarantee of anonymity. Review the final hosted page, downloadable PDF, asset metadata, source
repository exposure, and any replacement media before sharing the link.
