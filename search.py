class OnlySearchDocView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        start_time = datetime.now()
        y = time.time()
        nouns = request.GET.get('nouns')  # 검색어 받기
        start_date = request.GET.get('start_date')  # 날짜 시작 받기
        end_date = request.GET.get('end_date')  # 날짜 끝 받기
        category = request.GET.get('category')  # 카테고리가 있으면 받기
        page = request.GET.get('page')  # 몇 페이지에 해당하는지 받기
        page_count = request.GET.get('page_count')  # 한 페이지에 얼마나 보여줄지 받기
        session = request.GET.get('session_id')  # 검색하는 사람의 세션 받기
        interaction = 1 if any('&' in s for s in nouns) else 0
        nouns_list = nouns.split('&')  # 검색어가 &를 포함하고 있으면 분리
        nn = [x.strip() for x in nouns_list]  # blank(띄워쓰기) 삭제
        sort = request.GET.get('sort')
        sort_type = request.GET.get('sort_type')
        # is_all: 전체 페이지 호출 여부 ('true', 'false')
        is_all = request.GET.get('is_all', 'false')
        if is_all == 'true':
            is_all = True
        else:
            is_all = False
        search_word = [lib_konlpy.ext_nouns(n) for n in nn]  # 명사만 추출하기 ex) 제조 금속 & 나노 전자 & 유전자 -> [['제조','금속'],['나노','전자'],[유전자]]
        list_nouns = lib_konlpy.ext_nouns(nouns)  # &에 관계없이 명사추출
        print('OnlySearchDocView')

        if not sort:
            sort = 'application_number'
        if not sort_type:
            sort_type = 'ascend'
        if not page:
            page = 1
        if not page_count:
            page_count = 10

        mecab = Mecab()
        if '&' in nouns:
            split_nouns = nouns.split('&')  # 검색어에 & 있으면 분리
        else:
            split_nouns = [nouns]  # 검색어에 & 없으면 형태에 맞게 변형

        nouns = []
        for i in split_nouns:  # 검색어를 &로 나눈 후 형태소 분석 하였을때, 고유명사, 명사, 숫자, 영어가 있는 확인 후 nouns에 저장
            nn = []
            x = mecab.pos(i)
            for a in x:
                if a[1] == 'NNG' or a[1] == 'NNP' or a[1] == 'SN' or a[1] == 'SL':
                    nn.append(a[0])
            nouns.append(nn)
            del x

        bold_nouns = [item for items in nouns for item in items]  # 볼드 처리해야할 단어들

        obj_list = []
        direct_query = []
        for i in nouns:  # nouns를 돌면서 고유명사, 명사, 숫자, 영어를 포함하는 object들을 들고옴
            for num, j in enumerate(i):
                if sort_type == 'ascend':
                    try:
                        application_number = int(j)
                        obj_content = Document.objects.defer('summary', 'claim').filter(
                            Q(content__icontains=j) | Q(title_english__icontains=j) | Q(application_number__icontains=application_number)).order_by(sort)
                    except Exception as e:
                        obj_content = Document.objects.defer('summary', 'claim').filter(Q(content__icontains=j) | Q(title_english__icontains=j)).order_by(sort)
                else:
                    try:
                        application_number = int(j)
                        obj_content = Document.objects.defer('summary', 'claim').filter(
                            Q(content__icontains=j) | Q(title_english__icontains=j) | Q(application_number__icontains=application_number)).order_by('-'+sort)
                    except Exception as e:
                        obj_content = Document.objects.defer('summary', 'claim').filter(Q(content__icontains=j) | Q(title_english__icontains=j)).order_by('-'+sort)
                if num == 0:
                    obj_list = obj_content
                else:
                    obj_list = obj_content


        if is_all:
            instance = obj_list.all()
            total_page = 0
            total_documents = 0
        else:
            p = Paginator(obj_list, page_count)
            instance = p.page(page)
            total_page = p.num_pages
            total_documents = p.count

        for obj in instance:# 볼드 처리해야할 단어들이 내용에 몇번 포함되어 있는지 계산
            x = 0
            application_number = str(obj.application_number)
            content = obj.content
            for n in bold_nouns:
                if n in application_number:
                    x += 1
                if content:
                    x += obj.content.count(n)
            if x != 0:
                direct_query.append([obj, x])
        direct_query = sorted(direct_query, key=lambda item: item[1], reverse=True)  # 직접 검색 결과(정렬된 것)
        data = SearchResultSerializer([item[0] for item in direct_query], many=True).data

        for idx, value in enumerate(data):
            value['key'] = idx

        result = {
            'total_number': len(direct_query),
            'bold': bold_nouns,
            'data': data,
            'page': page,
            'page_count': page_count,
            'total_page': total_page,
            'total_documents': total_documents
        }
        return Response(
            status=status.HTTP_200_OK,
            data=GeneralResponse(
                200,
                'search, OnlySearchDoc, get',
                result
            ).response
        )
