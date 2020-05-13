# (c) 2020 Michał Górny
# 2-clause BSD license

"""Gander privacy policy"""

# this is in .py, so we can reliably import it without jumping through
# hoops

PRIVACY_POLICY = """
============================
Goose project privacy policy
============================

Please note that the project is in an early experimental stage.
Its code as well as this policy is still subject to changes.


1. The purpose of the Goose project is to collect anonymous statistics
   related to Gentoo packages, in order to aid Gentoo developers
   and users in decision making.  The statistics are public.

2. Participation in the project is entirely voluntary and opt-in.
   Gander does not submit any data unless you explicitly request setup
   and accept this privacy policy.

3. Any non-editorial changes to this privacy policy will require
   explicit acceptance.  Until then, Gander will either submit reduced
   data according to the previously accepted version of the policy,
   or stop operating if it becomes no longer meaningful.

4. The following information is collected for your system
   for statistical purposes:

   - the list of selected installed packages (@world)
   - the active profile

   The collected information is filtered to items present in the Gentoo
   repository.

5. Additionally, the following information is included in the reports:

   - the version of the spec that the submission is confirming to,
     that is far less granular than gander release versions
   - a system identifier that is randomly generated during the setup
     phase and that is used to prevent accidental duplicate submissions

6. In addition to that, we may collect the IP addresses that are used
   for submissions to enforce submission limits.  Additional information
   about HTTP requests may be stored temporarily in server logs.

7. The submissions are sent over HTTPS to a server controlled by Gentoo
   Infrastructure team.  The confidentiality of submissions therefore
   relies on security of the TLS infrastructure, the server and Gentoo
   Infrastructure team members.

8. Upon receiving the report, the server-side application immediately
   decomposes it and discards the original.  Only counts of individual
   items present in the report are stored in the database.

9. The publicly visible statistics are updated periodically from new
   reports.  The submitted data is stored for 7 days, after which it is
   discarded.  A configured Gander instance submits new reports every
   7 days.
""".strip()
