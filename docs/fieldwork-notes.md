# Fieldwork notes

Events during fieldwork that affect the evidence or the results, in the order they happened. Times are UTC.

| When | What happened | Effect on the review |
|---|---|---|
| 27 October, before 03:02 | The domain controller's clock was found about 38 minutes slow and was corrected with `chronyc makestep`. | Directory evidence was extracted after the correction. Recorded as a limitation of the logical access review and in OP-06 (F22). |
| 27 October, 03:02 | Directory evidence extracted (`evidence/directory-20261027T030229Z`). | Evidence for AC-01 to AC-14, and the end of period directory used by AC-18 and CM-04. |
| 27 October, 03:35 | Remediation applied on the domain controller and a fresh extraction taken (`evidence/directory-20261027T033513Z`). | Used only for the logical access retest. |
| 28 October, 01:47 | Joining the app server to the domain failed. The domain controller's clock was about 22 hours behind, and Kerberos rejects clocks more than 5 minutes apart. It was corrected by restarting chrony. | Recorded in OP-06 (F22). |
| 28 October, 01:51 | The join failed again because the domain Administrator password was not accepted. The lab administrator reset the built in Administrator password on the domain controller and joined the server. | The built in Administrator account is outside the access tests. The directory evidence used was extracted the day before, so the reset does not appear in it. |
| 28 October, 01:54 | The app server was built and evidence extracted from it and from both servers (`evidence/app-20261028T015418Z`, `evidence/host-linux2-20261028T015418Z`, `evidence/host-linux-20261028T015420Z`). | Evidence for AC-15 to AC-18, CM-01 to CM-07 and OP-01 to OP-07. |
| 28 October | The office PC had not been put into service. | The PC items in the test plan (part of AC-15, AC-16, OP-06 and OP-07) were not tested. The PC will be reviewed once it is in service. |
