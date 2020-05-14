
import logging
import uuid

from django.http import HttpResponse
from django.shortcuts import render
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
import os
import time, random
from models import Document
import xmltodict
import urllib
import datetime
from gensim.models.doc2vec import Doc2Vec
import library.lib_konlpy as lib_konlpy
from scipy.stats import beta
import re, math
from django.core.files import File

# pdfminer.six
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
from io import StringIO

class DataApi(APIView): 
    permission_classes = (AllowAny,)

    def __collect(self, data):
        url = 'http://futures-plani.com:5964/collect/'
        response = requests.post(url, data)
        print(response.status_code)
        print(response.text)

    def post(self, request):
        i = 0
        have_to_be_obj = DocumentStatus.objects.all()
        have_to_be_str = have_to_be_obj[0].have_to_be_list
        have_to_be_str = have_to_be_str.split('|')
        have_to_be_str.pop()
        have_to_be_patent_number = [int(x) for x in have_to_be_str]
        instance = APIKey.objects.get(id=1)
        api_key = instance.key

        # if not have_to_be_patent_number:
        #     temp = []
        #     patents = Document.objects.all()
        #     for patent in patents:
        #         temp.append(patent.application_number)
        #     have_to_be_patent_number = temp

        for patent_number in have_to_be_patent_number:
            try:
                patent_obj = Document.objects.filter(application_number=patent_number)
                print(patent_obj, patent_number)

                rd = requests.get(
                    'http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getBibliographyDetailInfoSearch?applicationNumber={}&ServiceKey={}'.format(
                        patent_number, api_key))
                html = rd.text
                data = xmltodict.parse(html)
                biblioSummaryInfo = data['response']['body']['item']['biblioSummaryInfoArray']['biblioSummaryInfo']
                judging_progress_status = biblioSummaryInfo['finalDisposal']
                legal_status = biblioSummaryInfo['registerStatus']
                title_korean = biblioSummaryInfo['inventionTitle']
                title_english = biblioSummaryInfo['inventionTitleEng']
                application_number = biblioSummaryInfo['applicationNumber'].replace('-', '')
                application_date = biblioSummaryInfo['applicationDate'].replace('.', '-')
                registration_number = biblioSummaryInfo['registerNumber']
                registration_date = biblioSummaryInfo['registerDate']
                release_number = biblioSummaryInfo['openNumber']
                release_date = biblioSummaryInfo['openDate']
                if release_number != None: release_number = release_number.replace('-','')
                if release_date != None: release_date = release_date.replace('.','-')
                if registration_number != None: registration_number = registration_number.replace('-', '')
                if registration_date != None: registration_date = registration_date.replace('.', '-')
                abstract = data['response']['body']['item']['abstractInfoArray']['abstractInfo']['astrtCont']
                claimInfoArray = data['response']['body']['item']['claimInfoArray']['claimInfo']
                claim = ''
                for c in claimInfoArray: claim += c['claim'] + '|'
                applicantInfo = data['response']['body']['item']['applicantInfoArray']['applicantInfo']
                applicant = ''
                try:
                    if len(applicantInfo) != 1:
                        for applicate in applicantInfo:
                            applicant += applicate['name'] + '|'
                except:
                    applicant = applicantInfo['name'] + '|'
                inventorInfo = data['response']['body']['item']['inventorInfoArray']['inventorInfo']
                inventorname = ''
                inventor_english = ''
                try:
                    for inventor in inventorInfo: inventorname += inventor['name'] + '|'
                    for inventoreng in inventorInfo: inventor_english += inventoreng['engName'].replace(',', '') + '|'
                except:
                    inventorname = inventorInfo['name'] + '|'
                    inventor_english = inventorInfo['engName'].replace(',', '') + '|'
                rd = requests.get(
                    'http://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice/patentFamilyInfo?applicationNumber={}&accessKey={}'.format(
                        patent_number, api_key))
                html = rd.text
                data = xmltodict.parse(html)
                patentFamilyInfo = data['response']['body']['items']
                countryCode, countryName, literatureKind, familyNumber, familyKind = '', '', '', '', ''
                if patentFamilyInfo != None:
                    patentFamilyInfo = patentFamilyInfo['patentFamilyInfo']
                    try:
                        for patentFamily in patentFamilyInfo:
                            countryCode += patentFamily['countryCode'] + '|'
                            countryName += patentFamily['countryName'] + '|'
                            literatureKind += patentFamily['literatureKind'] + '|'
                            familyNumber += patentFamily['familyNumber'] + '|'
                            familyKind += patentFamily['familyKind'] + '|'
                    except:
                        countryCode = patentFamilyInfo['countryCode'] + '|'
                        countryName = patentFamilyInfo['countryName'] + '|'
                        literatureKind = patentFamilyInfo['literatureKind'] + '|'
                        familyNumber = patentFamilyInfo['familyNumber'] + '|'
                        familyKind = patentFamilyInfo['familyKind'] + '|'

                jpgDir, pdfDir, htmlDir = None, None, None
                jpgName = os.getcwd() + '/jpg_directory/' + str(patent_number) + '.jpg'
                pdfName = os.getcwd() + '/pdf_directory/' + str(patent_number) + '.pdf'
                registrationPdfName = os.getcwd() + '/pdf_registration_directory/' + str(patent_number) + '_registration.pdf'
                htmlName = os.getcwd() + '/html_directory/' + str(patent_number) + '.html'
                if os.path.isfile(jpgName): jpgDir = jpgName
                if os.path.isfile(pdfName): pdfDir = pdfName
                if os.path.isfile(registrationPdfName): registrationPdfDir = registrationPdfName
                if os.path.isfile(htmlName): htmlDir = htmlName

                data = {
                    'title_korean': title_korean,
                    'title_english': title_english,
                    'applicant': applicant,
                    'application_number': application_number,
                    'application_date': application_date,
                    'registration_number': registration_number,
                    'registration_date': registration_date,
                    'release_number': release_number,
                    'release_date': release_date,
                    'summary': abstract,
                    'legal_status': legal_status,
                    'judging_progress_status': judging_progress_status,
                    'claim': claim,
                    'quotation': None,
                    'cited': None,
                    'family_country_code': countryCode,
                    'family_country_name': countryName,
                    'family_number': familyNumber,
                    'family_literature_kind': literatureKind,
                    'family_kind': familyKind,
                    'inventor': inventor,
                    'inventor_english': inventor_english
                }

                if len(Document.objects.filter(application_number=patent_number)) == 0:
                    print(patent_obj, '새로운 특허입니다')

                    obj = Document(
                        title_korean=title_korean, title_english=title_english,
                        applicant=applicant, application_number=application_number, application_date=application_date,
                        registration_number=registration_number, registration_date=registration_date,
                        release_number=release_number, release_date=release_date,
                        summary=abstract, claim=claim, family_country_code=countryCode,
                        family_country_name=countryName, family_number=familyNumber,
                        family_literature_kind=literatureKind, family_kind=familyKind,
                        inventor=inventorname, inventor_english=inventor_english,
                        figure_path=jpgDir, pdf_path=pdfDir, regisration_pdf_dir=registrationPdfDir,  html_path=htmlDir,
                        legal_status=legal_status, judging_progress_status=judging_progress_status
                    )
                    obj.save()
            except Exception as e:
                print(e)

                # self.__collect(data)

            else:
                print(patent_obj, '존재하는 특허가 업데이트됩니다')
                patent_obj = patent_obj[0]
                patent_obj.title_korean = title_korean
                patent_obj.title_english = title_english
                patent_obj.applicant = applicant
                patent_obj.application_number = application_number
                patent_obj.application_date = application_date
                patent_obj.registration_number = registration_number
                patent_obj.registration_date = registration_date
                patent_obj.release_number = release_number
                patent_obj.release_date = release_date
                patent_obj.summary = abstract
                patent_obj.claim = claim
                patent_obj.family_country_code = countryCode
                patent_obj.family_literature_kind = literatureKind
                patent_obj.family_kind = familyKind
                patent_obj.inventor = inventorname
                patent_obj.inventor_english = inventor_english
                patent_obj.figure_path = jpgDir
                patent_obj.pdf_path = pdfDir
                patent_obj.html_path = htmlDir
                patent_obj.legal_status = legal_status
                patent_obj.judging_progress_status = judging_progress_status
                patent_obj.save()

                # self.__collect(data)
            random_int = random.randint(3, 5)
            time.sleep(random_int)

        return Response(
            status=status.HTTP_200_OK,
            data=GeneralResponse(
                200,
                'crawldb',
                {}
            ).response
        )


class DownloadDoc(APIView):  # getseq에 의해 찾아진 업데이트 혹은 더 받아야할 출원번호의 pdf파일과 대표 이미지를 받는 api
    permission_classes = (AllowAny,)

    def post(self, request):
        possess_patents = Document.objects.all()
        possess_application_number = [obj.application_number for obj in possess_patents]  # 보유하고 있는 특허
        kipris_patents = DocumentStatus.objects.all()
        kipris_patent = kipris_patents[0]
        kipris_possess_patents = kipris_patent.now_patent_all  # 보유하고 있지 않은 것
        transferinfo = kipris_patent.transferinfo  # 보유하고 있는 것 중에 업데이트 되어야 하는 것
        kipris_possess_patent_list, updated_transferinfo_list = [], []

        instance = APIKey.objects.get(id=1)
        api_key = instance.key
        print(api_key)

        if not len(kipris_possess_patents) == 0:
            kipris_possess_patent_list = kipris_possess_patents.split('|')
            kipris_possess_patent_list.pop()
        if not len(transferinfo) == 0:
            updated_transferinfo_list = transferinfo.split('|')
            updated_transferinfo_list.pop()
        from_kipris_patent_all = kipris_possess_patent_list + updated_transferinfo_list
        from_kipris_patent_all = [int(i) for i in from_kipris_patent_all]
        data = list(set(from_kipris_patent_all) - set(possess_application_number))
        data_str = ''
        for d in data:
            print(d)
            data_str += str(d) + '|'

        kipris_patent.have_to_be_list = data_str
        kipris_patent.save()

        patents_list = []
        if not data:
            temp = []
            patents = Document.objects.all()
            for patent in patents:
                temp.append(patent.application_number)
            patents_list = temp

        for patent_number in patents_list:
            print('Downloading {}'.format(patent_number))
            try:
                resp = requests.get(
                    'http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAnnFullTextInfoSearch?applicationNumber={}&ServiceKey={}'.format(
                        str(patent_number), api_key))
                html = resp.text
                data = xmltodict.parse(html)
                docName = settings.MEDIA_ROOT + 'pdf_directory/' + str(patent_number) + '.pdf'
                pdfUrl = data['response']['body']['item']['path']
                urllib.request.urlretrieve(pdfUrl, docName)
            except Exception as e:
                log.exception(e)
                print(patent_number, 'no application pdf')

        for patent_number in patents_list:
            print('Downloading {}'.format(patent_number))
            try:
                resp1 = requests.get(
                    'http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getPubFullTextInfoSearch?applicationNumber={}&ServiceKey={}'.format(
                        str(patent_number), api_key))
                html1 = resp1.text
                data1 = xmltodict.parse(html1)
                docName1 = settings.MEDIA_ROOT + 'pdf_registration_directory/' + str(
                    patent_number) + '.pdf'
                pdfUrl1 = data1['response']['body']['item']['path']
                urllib.request.urlretrieve(pdfUrl1, docName1)
            except Exception as e:
                log.exception(e)
                print(patent_number, 'no registration pdf')

        for patent_number in patents_list:
            resp = requests.get(
                'http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getReprsntFloorPlanInfoSearch?applicationNumber={}&ServiceKey={}'.format(
                    str(patent_number), api_key))
            html = resp.text
            data = xmltodict.parse(html)
            try:
                docName = settings.MEDIA_ROOT + 'jpg_directory/' + str(patent_number) + '.jpg'
                jpgUrl = data['response']['body']['imagePathInfo']['largePath']
                urllib.request.urlretrieve(jpgUrl, docName)
                print(docName, jpgUrl)
            except Exception as e:
                log.exception(e)
                print(patent_number, 'no image')

        return Response(
            status=status.HTTP_200_OK,
            data=GeneralResponse(
                200,
                'Download PDF',
                {}
            ).response
        )
