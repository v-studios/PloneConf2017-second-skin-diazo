#!/usr/bin/env python

from selenium import webdriver
# from selenium.common.exceptions import WebDriverException
# from selenium.webdriver.common.by import By
# from selenium.common.exceptions import TimeoutException
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from os import environ
from time import sleep
from unittest import TestCase, main

BASE = 'http://CANONICAL.DNSNAME.v-studios.com'

# NOTE: we don't commit passwords to code, so for authenticated test to pass,
# set your environment vars:
# - export TTT_MEMBER_USERNAME="..."
# - export TTT_MEMBER_PASSWORD="..."
# - export TTT_ADMIN_USERNAME="..."
# - export TTT_ADMIN_PASSWORD="..."

# We use Firefox so devs don't need to "brew install chromedriver"

# In many tests, we can't compare full text as the text is Windows chars using
# \xa0 for space and similar \xe2 for dash


###############################################################################
# Public/Anonymous pages
# removed: '/trade-to-travel-news.asp'

# Home page

class TestHome(TestCase):
    def setUp(self):
        self.url = BASE + '/'
        self.title = 'Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)

    def testLinkLearnMoreAboutMembership(self):
        self.browser.find_element_by_link_text('LEARN MORE ABOUT MEMBERSHIP').click()
        self.assertEqual(self.browser.title,
                         'Free Trial Membership | Trade to Travel')

    def testLinkTestimonials(self):
        self.browser.find_element_by_link_text('MORE TESTIMONIALS').click()
        self.assertEqual(self.browser.title,
                         'Testimonials | Trade to Travel')

    # TODO: test sample search, video, links
    # TODO: Footer Links...


# Who We Are

class TestWhoWeAre_AboutUs(TestCase):
    def setUp(self):
        self.url = BASE + '/luxury-home-exchange.asp'
        self.title = 'Who We Are | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)

    # In links, why do URL IDs (361) not match property number (261)?

    def testPropertyLinkStJames(self):
        self.browser.find_element_by_link_text('Bon Vivant Villa, Barbados').click()
        self.assertIn('St. James', self.browser.title)
        # Trade to Travel Property #T261')

    def testPropertyLinkKenmare(self):
        self.browser.find_element_by_partial_link_text('Park Hotel').click()
        self.assertIn('Kenmare', self.browser.title)
        # Trade to Travel Property #T195')

    def testPropertyLinkCayoEspanto(self):
        self.browser.find_element_by_link_text('Cayo Espanto Private Island, Belize').click()
        self.assertIn('Cayo Espanto', self.browser.title)
        # Trade to Travel Property #T456A')

    def testPropertyLinkUSSSequoia(self):
        self.browser.find_element_by_partial_link_text('USS Sequoia').click()
        self.assertIn('Washington, District of Columbia', self.browser.title)


class TestWhoWeAre_OurStory(TestCase):

    def setUp(self):
        self.url = BASE + '/trade-to-travel-story.asp'
        self.title = u'Our Story | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


class TestWhoWeAre_Testimonials(TestCase):

    def setUp(self):
        self.url = BASE + '/testimonials-referrals.asp'
        self.title = u'Testimonials | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


class TestWhoWeAre_News(TestCase):

    def setUp(self):
        self.url = BASE + '/trade-to-travel-newsletter.asp'
        self.title = u'Newsletter Archives | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


# How We Work

class TestHowWeWork_MemberInfo(TestCase):

    def setUp(self):
        self.url = BASE + '/luxury-property-exchange.asp'
        self.title = u'How We Work | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)

    def testFAQsRevealConceal(self):
        # TODO: use expected_condition and maybe
        # visibility_of_element_located_by to wait for reveal or
        # conceal to finish before counting (in)visible answers.
        #
        # No invisibility check for selenium object;
        # this only waits for the first (?) to become invisible
        #  wait = WebDriverWait(self.browser, 10)
        #  wait.until(EC.invisibility_of_element_located((By.CLASS_NAME, 'hidden')))
        # We can pass the answer object here
        #  wait = WebDriverWait(self.browser, 10)
        #  wait.until(EC.visibility_of(answers[3]))
        # See http://stackoverflow.com/questions/7781792/selenium-waitforelement
        # Should be more clever finding FAQ and Answer pairs.
        # Could also use: answer[0].get_attribute('style')

        faqs = self.browser.find_elements_by_class_name('show')
        self.assertEqual(len(faqs), 4)
        answers = self.browser.find_elements_by_class_name('hidden')
        self.assertEqual(len(answers), 4)
        displayed = [a for a in answers if a.is_displayed()]
        self.assertEqual(len(displayed), 0)
        # Reveal
        for faq in faqs:
            faq.click()     # open
        sleep(1)            # hack: make take a sec to reveal
        displayed = [a for a in answers if a.is_displayed()]
        self.assertEqual(len(displayed), 4)
        # Conceal again
        for faq in faqs:
            faq.click()     # close
        sleep(1)                # hack: may take a sec to conceal
        displayed = [a for a in answers if a.is_displayed()]
        self.assertEqual(len(displayed), 0)


class TestHowWeWork_MemberApplication(TestCase):

    def setUp(self):
        self.url = BASE + '/MembershipAppOnline.asp'
        self.title = u'Membership Application | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


class TestHowWeWork_FreeTial(TestCase):

    def setUp(self):
        self.url = BASE + '/membership-information.asp'
        self.title = u'Free Trial Membership | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


class TestHowWeWork_ReferralReward(TestCase):

    def setUp(self):
        self.url = BASE + '/ReferReward.asp'
        self.title = u'Referral Rewards | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


class TestHowWeWork_WhyTTT(TestCase):

    def setUp(self):
        self.url = BASE + '/luxury-travel-club.asp'
        self.title = u'Why Trade to Travel? | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


# Properties - Search

class TestProperties_Search(TestCase):

    def setUp(self):
        self.url = BASE + '/vacation-property-search.asp'
        self.title = u'Property Search | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)

    def testSearchPropertyCode(self):
        # Can't yet find the search button as it has no link text, just img
        self.browser.find_element_by_id('txtPropCode').send_keys('T2731')
        self.browser.find_element_by_xpath('//table/tbody/tr/td/a').click()
        self.assertEqual(self.browser.find_element_by_id('page-title').text,
                         u'PROPERTY SEARCH RESULTS')
        self.assertEqual(self.browser.title,
                         u'Property Search - Results | Trade to Travel')

    def testSearchResultInfoRent(self):
        # Verify the "Click here for more info..." and "Rent This Property"
        # links, both of which create new windows we have to switch to.
        # We do NOT fill in the Rent info request form!
        self.browser.find_element_by_id('txtPropCode').send_keys('T2731')
        self.browser.find_element_by_xpath('//table/tbody/tr/td/a').click()
        # This pops a new window, save ours before switching
        this_window = self.browser.current_window_handle
        self.browser.find_element_by_partial_link_text(
            'Click here for more information').click()
        # Why doesn't this work: self.browser.switch_to_window('_blank')
        for w in self.browser.window_handles:
            if w != self.browser.current_window_handle:
                self.browser.switch_to_window(w)
                break
        self.assertIn('Barcelona', self.browser.title)
        self.assertIn('#T2731', self.browser.title)
        self.browser.close()
        self.browser.switch_to.window(this_window)
        # Seems odd we don't need to be authenticated to do the request
        self.browser.find_element_by_link_text('RENT THIS PROPERTY').click()
        for w in self.browser.window_handles:
            if w != self.browser.current_window_handle:
                self.browser.switch_to_window(w)
                break
        self.assertEqual(self.browser.title, 'Information Request')

    def testSearchKeywords(self):
        self.browser.find_element_by_id('txtKeywords').send_keys('barcelona')
        self.browser.find_element_by_id('btnReport').click()
        self.assertEqual(self.browser.find_element_by_id('page-title').text,
                         u'PROPERTY SEARCH RESULTS')
        self.assertEqual(self.browser.title,
                         u'Property Search - Results | Trade to Travel')

    def testSearchPropType(self):
        proptypes = Select(self.browser.find_element_by_id('cboPropType'))
        proptypes.deselect_all()
        proptypes.select_by_visible_text('Islands')
        proptypes.select_by_visible_text('Metropolitan')
        self.browser.find_element_by_id('btnReport').click()
        self.assertEqual(self.browser.find_element_by_id('page-title').text,
                         u'PROPERTY SEARCH RESULTS')
        self.assertEqual(self.browser.title,
                         u'Property Search - Results | Trade to Travel')

    def testSearchManySelections(self):
        # I should be testing search on individual fields:
        #  cboFeatures cboGeoLocation cboSpecialAccommodations cboPropLocation
        #  txtBedrooms txtBAthrooms txtOccupancy
        #  txtMinPoints txtMaxPoints
        #  chkMemberOwned chkRental chkTimeShare chkSale chkNew
        # But for now, just fill a bunch out and get results
        proptypes = Select(self.browser.find_element_by_id('cboPropType'))
        proptypes.deselect_all()
        proptypes.select_by_visible_text('Metropolitan')
        geoloc = Select(self.browser.find_element_by_id('cboGeoLocation'))
        geoloc.select_by_visible_text('Europe')
        Select(self.browser.find_element_by_id('cboPropLocation')).select_by_visible_text('Walk to sandy beach')
        self.browser.find_element_by_id('txtBedrooms').send_keys('3')
        self.browser.find_element_by_id('txtBathrooms').send_keys('2')
        self.browser.find_element_by_id('txtOccupancy').send_keys('4')
        self.browser.find_element_by_id('txtMinPoints').send_keys('1')
        self.browser.find_element_by_id('txtMaxPoints').send_keys('2')
        btn = self.browser.find_element_by_id('chkMemberOwned')
        if not btn.is_selected():
            btn.click()
        self.browser.find_element_by_id('btnReport').click()
        self.assertEqual(self.browser.find_element_by_id('page-title').text,
                         u'PROPERTY SEARCH RESULTS')
        self.assertEqual(self.browser.title,
                         u'Property Search - Results | Trade to Travel')


class TestProperties_SampleAvailabilities(TestCase):

    def setUp(self):
        self.url = BASE + '/vacation-properties-future.asp'
        self.title = u'Availabilities | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


class TestProperties_HotelsResortsSpas(TestCase):

    def setUp(self):
        self.url = BASE + '/hotel-exchange.asp'
        self.title = u'Hotels, Resorts & Spas | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


class TestProperties_ForSale(TestCase):

    def setUp(self):
        self.url = BASE + '/browse-properties-forsale.asp'
        self.title = u'Sale | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


class TestProperties_ForCharities(TestCase):

    def setUp(self):
        self.url = BASE + '/charities.asp'
        self.title = u'For Charities | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


class TestProperties_FractionalOwnership(TestCase):

    def setUp(self):
        self.url = BASE + '/BrowseFractional.asp'
        self.title = u'Fractional Ownership| Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


# TODO: No, this isn't how we test footer: we need to find links on the main
# (or other) page and then click them and check the title.

class TestFooter_SiteMap(TestCase):

    def setUp(self):
        self.url = BASE + '/site-map.asp'
        self.title = u'Sitemap | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


class TestFooter_MoneyBackGuarantee(TestCase):

    def setUp(self):
        self.url = BASE + '/money-back-guarantee.asp'
        self.title = 'Money-Back Guarantee | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertEqual(self.browser.title, self.title)


class TestPropertiesViewPretty(TestCase):
    # Accessible from results of various searches.
    # Just try one for now.
    def setUp(self):
        self.url = BASE + '/propertiesViewPretty.asp?property_ID=2573'
        self.in_title = u'Barcelona'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def testPageTitle(self):
        self.assertIn(self.in_title, self.browser.title)


###############################################################################
# Members: require authentication

class TestMemberLogin(TestCase):

    def setUp(self):
        self.url = BASE + '/member-login.asp'
        self.title = u'Login | Trade to Travel'
        self.browser = webdriver.Firefox()
        self.addCleanup(self.browser.quit)
        self.browser.get(self.url)

    def _login(self):
        # Helper function since we'll login for every page
        # Get creds from environment so we don't commit them in code;
        # if not found, all the dependent tests fail, as they should.
        # Clicking on the login button does nothing, it's javascript
        self.assertIn('TTT_MEMBER_USERNAME', environ)
        self.assertIn('TTT_MEMBER_PASSWORD', environ)
        username = environ['TTT_MEMBER_USERNAME']
        password = environ['TTT_MEMBER_PASSWORD']
        self.browser.find_element_by_name('txtUserName').send_keys(username)
        self.browser.find_element_by_name('txtPassword').send_keys(password)
        self.browser.find_element_by_id('user-login_form').submit()

    def testPageTitle(self):
        self.assertIn(self.title, self.browser.title)

    def testLogin(self):
        self._login()
        self.assertTrue(self.browser.current_url.endswith('MemberMain.asp'))
        self.assertIn('Vacation Rentals, Home Exchange, Vacation Home',
                      self.browser.title)

    def testMyAccountInfo(self):
        self._login()
        self.browser.find_element_by_link_text('My Account Info').click()
        self.assertIn('CustomerEdit.asp', self.browser.current_url)

    def testMyFavoriteProperties(self):
        self._login()
        self.browser.find_element_by_link_text('My Favorite Properties').click()
        self.assertIn('FavoritePropertyList.asp', self.browser.current_url)

    def testMyDesiredDestinations(self):
        self._login()
        self.browser.find_element_by_link_text('My Desired Destinations').click()
        self.assertIn('DesiredDestinations.asp', self.browser.current_url)

    def testReferralRewards(self):
        self._login()
        self.browser.find_element_by_link_text('Referral Rewards').click()
        self.assertIn('ReferReward.asp', self.browser.current_url)

    def testMyProperties(self):
        self._login()
        self.browser.find_element_by_link_text('My Properties').click()
        self.assertIn('PropertySearchResults.asp', self.browser.current_url)

    def testMyAddANewProperty(self):
        self._login()
        self.browser.find_element_by_link_text('Add a New Property').click()
        self.assertIn('PropertiesAddNew.asp', self.browser.current_url)

    def testLogout(self):
        # The <a> is around an image so harder to find
        self._login()
        self.browser.find_element_by_xpath("//a[@href='Logout.asp']").click()
        self.assertTrue(self.browser.current_url.endswith('/'))

###############################################################################
# Admins: require authentication

###############################################################################
# Main: convenience if run directly, e.g., from Makefile

if __name__ == '__main__':
    """You could run all tests by invoking this file.

    Or you can be selective like::
      py.test tests/browser_tests.py::TestHowWeWork_MemberInfo
      py.test tests/browser_tests.py::TestProperties_Search::testSearchManySelections
    """
    main(verbosity=2)
