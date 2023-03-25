test: test1 test2 test3 test3legacy test4 test5 test6 test7 test8 test9 test10 test11 test12 test14 test15 test16 \
      test17 test18 test19 test20 test21 test22 test23 test24 test25

test1:
	# Test help
	$(PYANG) --sid-help 2>&1 | diff -b test-1-expected-output.txt -

test2:
	# Test generate sid file
	$(PYANG) --sid-list --sid-generate-file 20000:25 toaster@2009-11-20.yang 2>&1 | diff -b test-2-expected-output.txt -
	diff -b test-2-expected-toaster@2009-11-20.sid toaster@2009-11-20.sid
	$(PYANG) --sid-check-file-valid toaster@2009-11-20.sid toaster@2009-11-20.yang 2>&1 | diff -b test-expected-output-when-valid.txt -
	rm toaster@2009-11-20.sid

test3:
	# Test update sid file
	cp test-2-expected-toaster@2009-11-20.sid toaster@2009-11-20.sid
	$(PYANG) --sid-list --sid-update-file toaster@2009-11-20.sid toaster@2009-12-28.yang 2>&1 | diff -b test-3-expected-output.txt -
	diff -b test-3-expected-toaster@2009-12-28.sid toaster@2009-12-28.sid
	$(PYANG) --sid-check-file-valid toaster@2009-12-28.sid toaster@2009-12-28.yang 2>&1 | diff -b test-expected-output-when-valid.txt -
	rm toaster@2009-11-20.sid toaster@2009-12-28.sid

test3legacy:
	# Test update sid file (legacy JSON format, remove when SidPlugin.upgrade_sid_file_format() is removed)
	cp test-2-expected-toaster-legacy@2009-11-20.sid toaster@2009-11-20.sid
	$(PYANG) --sid-list --sid-update-file toaster@2009-11-20.sid toaster@2009-12-28.yang 2>&1 | diff -b test-3-expected-output.txt -
	diff -b test-3-expected-toaster@2009-12-28.sid toaster@2009-12-28.sid
	$(PYANG) --sid-check-file-valid toaster@2009-12-28.sid toaster@2009-12-28.yang 2>&1 | diff -b test-expected-output-when-valid.txt -
	rm toaster@2009-11-20.sid toaster@2009-12-28.sid

test4:
	# Test check sid file
	cp test-2-expected-toaster@2009-11-20.sid toaster@2009-11-20.sid
	$(PYANG) --sid-list --sid-check-file toaster@2009-11-20.sid toaster@2009-11-20.yang 2>&1 | diff -b test-4-expected-output.txt -
	rm toaster@2009-11-20.sid

test5:
	# Test augment and yang data
	$(PYANG) --sid-generate-file 2500:50 ietf-constrained-voucher@2019-08-01.yang 2>&1 | diff -b test-5-expected-output.txt -
	diff -b test-5-expected-ietf-constrained-voucher@2019-08-01.sid ietf-constrained-voucher@2019-08-01.sid
	$(PYANG) --sid-check-file-valid ietf-constrained-voucher@2019-08-01.sid ietf-constrained-voucher@2019-08-01.yang 2>&1 | diff -b test-expected-output-when-valid.txt -
	rm ietf-constrained-voucher@2019-08-01.sid
  
test6:
	# Test SID range exhausted
	cp test-3-expected-toaster@2009-12-28.sid toaster@2009-12-28.sid
	$(PYANG) --sid-update-file toaster@2009-12-28.sid toaster@2019-01-01.yang 2>&1 | diff -b test-6-expected-output.txt - 
	rm toaster@2009-12-28.sid

test7:
	# Test extra SID range
	cp test-2-expected-toaster@2009-11-20.sid toaster@2009-11-20.sid
	$(PYANG) --sid-update-file toaster@2009-11-20.sid toaster@2009-12-28.yang --sid-extra-range 20010:10 2>&1 | diff -b test-7b-expected-output.txt -
	cp test-3-expected-toaster@2009-12-28.sid toaster@2009-12-28.sid
	$(PYANG) --sid-update-file toaster@2009-12-28.sid toaster@2019-01-01.yang --sid-extra-range 20100:25 2>&1 | diff -b test-7-expected-output.txt -
	diff -b test-7-expected-toaster@2019-01-01.sid toaster@2019-01-01.sid
	$(PYANG) --sid-check-file-valid toaster@2019-01-01.sid toaster@2019-01-01.yang 2>&1 | diff -b test-expected-output-when-valid.txt -
	rm -f toaster@2009-11-20.sid toaster@2009-12-28.sid toaster@2019-01-01.sid

test8:
	# In generate sid file, test count 
	$(PYANG) --sid-generate-file count toaster@2009-11-20.yang 2>&1 | diff -b test-8-expected-output.txt -

test9:
	# In generate sid file, test invalid SID range
	$(PYANG) --sid-generate-file 2000025 toaster@2009-11-20.yang 2>&1 | diff -b test-9-expected-output.txt -

test10:
	# In generate sid file, test invalid yang filename
	$(PYANG) --sid-list --sid-generate-file 20000:25 test10-bad-toaster@2009-11-20.yang 2>&1 | diff -b test-10-expected-output.txt -

test11:
	# In generate sid file, test yang file not found
	$(PYANG) --sid-generate-file 20000:25 toaster@2009-01-01.yang 2>&1 | diff -b test-11-expected-output.txt -

test12:
	# In update sid file, test count
	cp test-3-expected-toaster@2009-12-28.sid toaster@2009-12-28.sid
	$(PYANG) --sid-update-file toaster@2009-12-28.sid toaster@2019-01-01.yang --sid-extra-range count 2>&1 | diff -b test-12-expected-output.txt -
	rm toaster@2009-12-28.sid

test14:
	# In update sid file, test yang file not found
	$(PYANG) --sid-update-file toaster@2009-11-20.sid toaster2009-12-29.yang 2>&1 | diff -b test-14-expected-output.txt -

test15:
	# In update sid file, test invalid sid file
	$(PYANG) --sid-update-file test15-bad-toaster@2009-11-20.sid toaster@2009-12-28.yang 2>&1 | diff -b test-15-expected-output.txt -

test16:
	# In update sid file, test invalid JSON format
	$(PYANG) --sid-update-file test16-bad-toaster@2009-11-20.sid toaster@2009-12-28.yang 2>&1 | diff -b test-16-expected-output.txt -

test17:
	# In update sid file, test sid file not found
	$(PYANG) --sid-update-file toaster@2009-11-20.sid toaster@2009-12-28.yang 2>&1 | diff -b test-17-expected-output.txt -

test18:
	# In checksid file, test yang file not found
	$(PYANG) --sid-check-file toaster@2009-11-20.sid toaster.yang 2>&1 | diff -b test-18-expected-output.txt -

test19:
	# In checksid file, test test sid file not found
	$(PYANG) --sid-check-file toaster@2009-11-20.sid toaster@2009-11-20.yang 2>&1 | sort | diff -b test-19-expected-output.txt -

test20:
	# Test multiple level of grouping
	$(PYANG) --sid-generate-file 60000:100 ieee802-dot1q-psfp@2020-07-07.yang 2>&1 | diff -b test-20-expected-output.txt -
	diff -b test-20-expected-ieee802-dot1q-psfp@2020-07-07.sid ieee802-dot1q-psfp@2020-07-07.sid
	$(PYANG) --sid-check-file-valid ieee802-dot1q-psfp@2020-07-07.sid ieee802-dot1q-psfp@2020-07-07.yang 2>&1 | diff -b test-expected-output-when-valid.txt -
	rm ieee802-dot1q-psfp@2020-07-07.sid

test21:
	# Test check sid file valid
	$(PYANG) --sid-list --sid-generate-file 1700:100 ietf-system@2014-08-06.yang 2>&1 | diff -b test-21-expected-output.txt -
	diff -b test-21-expected-ietf-system@2014-08-06.sid ietf-system@2014-08-06.sid
	$(PYANG) --sid-check-file-valid ietf-system@2014-08-06.sid ietf-system@2014-08-06.yang 2>&1 | diff -b test-expected-output-when-valid.txt -
	rm -f ietf-system@2014-08-06.sid

test22:
	# Test check sid file valid, for the example in draft-ietf-core-sid-20
	cp test-draft-core-sid-20-example-ietf-system@2014-08-06.sid ietf-system@2014-08-06.sid
	$(PYANG) --sid-check-file-valid ietf-system@2014-08-06.sid ietf-system@2014-08-06.yang 2>test22-stderr.txt 1>test22-stdout.txt | cat
	diff -b test-22b-expected-output.txt test22-stderr.txt
	diff -b test-22c-expected-output.txt test22-stdout.txt
	rm -f ietf-system@2014-08-06.sid test22-stderr.txt test22-stdout.txt

test23:
	# Test update sid file (legacy JSON format, remove when SidPlugin.upgrade_sid_file_format() is removed)
	cp test-23-ietf-system-legacy@2014-08-06.sid ietf-system@2014-08-06.sid
	$(PYANG) --sid-list --sid-update-file ietf-system@2014-08-06.sid ietf-system@2014-08-06.yang 2>&1 | diff -b test-23-expected-output.txt -
	diff -b test-23-expected-ietf-system@2014-08-06.sid ietf-system@2014-08-06.sid
	$(PYANG) --sid-check-file-valid ietf-system@2014-08-06.sid ietf-system@2014-08-06.yang 2>&1 | diff -b test-expected-output-when-valid.txt -
	rm -f ietf-system@2014-08-06.sid

test24:
	# Test generate sid file, module with submodule, no revisions
	$(PYANG) --sid-list --sid-generate-file 20000:25 test-24-mod.yang 2>&1 | diff -b test-24-expected-output.txt -
	diff -b test-24-expected-test-24-mod@unknown.sid test-24-mod@unknown.sid
	$(PYANG) --sid-check-file-valid test-24-mod@unknown.sid test-24-mod.yang 2>&1 | diff -b test-expected-output-when-valid.txt -
	rm -f test-24-mod@unknown.sid

test25:
	# Test check sid file with updated import that affects the mapping
	$(PYANG) --sid-list --sid-generate-file 36000:25 test-25-mod@2023-01-01.yang 2>&1 | diff -b test-25-expected-output.txt -
	cp test-25-dep@2023-03-01.notyang test-25-dep@2023-03-01.yang
	$(PYANG) --sid-list --sid-check-file test-25-mod@2023-01-01.sid test-25-mod@2023-01-01.yang 2>&1 | diff -b test-25b-expected-output.txt -
	$(PYANG) --sid-check-file-valid test-25-mod@2023-01-01.sid test-25-mod@2023-01-01.yang 2>&1 | diff -b test-25c-expected-output.txt -
	rm -f test-25-mod@2023-01-01.sid test-25-dep@2023-03-01.yang
