import os
import sys
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from config.errorCode import *
from config.kiwoomType import *
from PyQt5.QtTest import *

class Kiwoom(QAxWidget):
    def __init__(self):
        super().__init__()

        self.realType = RealType()

        ########이벤트 루프 모음########
        self.login_event_loop = None
        self.detail_account_info_event_loop = QEventLoop( )
        self.calculator_event_loop = QEventLoop()
        ###############################

        ####스크린 번호 모음####
        self.screen_my_info = "2000"
        self.screen_calculation_stock = "4000"
        self.screen_real_stock = "5000"
        self.screen_meme_stock = "6000"
        self.screen_start_stop_real = "1000"
        #########################
        
        #####변수 모음########
        self.account_num = None
        ######################

        ####계좌관련 변수######
        self.use_money = 0
        self.use_money_percent = 0.5

        #####종목 분석 용####
        self.calcul_data = []

        #####변수 모음######
        self.portfolio_stock_dict = {}
        self.account_stock_dict = {} #계좌잔고 평가 내역
        self.not_account_stock_dict = {}
        self.jango_dict = {}
        ###################

        self.get_ocx_instance()
        self.event_slots()
        self.real_event_slots()

        self.signal_login_commConnect()
        self.get_account_info()
        self.detail_account_info() #예수금 가져오는 것
        self.detail_account_mystock() #계좌평가 잔고 내역 요청
        self.not_concluded_account()#미체결 요청
        
        #self.calculator_fnc() #종목 분석용, 임시용
        self.read_code() #저장된 종목들 불러오기
        self.screen_number_setting() #스크린 번호

        #실시간 등록
        #장 시간 
        self.dynamicCall("SetRealReg(QString, QString, QString, Qstring)",self.screen_start_stop_real,'',self.realType.REALTYPE['장시작시간']['장운영구분'],'0')

        for code in self.portfolio_stock_dict.keys():
            screen_num = self.portfolio_stock_dict[code]['스크린번호']
            fids = self.realType.REALTYPE['주식체결']['체결시간']
            self.dynamicCall("SetRealReg(QString, QString, QString, Qstring)",screen_num,code,fids,'1')
            print("실시간 등록 코드: %s, 번호: %s" % (code, fids))

    def get_ocx_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1")
        

    def event_slots(self):
        self.OnEventConnect.connect(self.login_slot)
        self.OnReceiveTrData.connect(self.trdata_slot)
        self.OnReceiveMsg.connect(self.msg_slot)

    def real_event_slots(self):
        self.OnReceiveRealData.connect(self.realdata_slot)
        #주문에 대한 이벤트 처리
        self.OnReceiveChejanData.connect(self.chejan_slot)
    
    def login_slot(self, errCode):
        print(errorCode(errCode)) #errCode == 0 올바르게 연결

        self.login_event_loop.exit()
    
    def signal_login_commConnect(self):
        self.dynamicCall("CommConnect()")

        self.login_event_loop = QEventLoop()
        self.login_event_loop.exec_()

    ####내 정보 가져오기
    def get_account_info(self):
        account_list = self.dynamicCall("GetLoginInfo(String)","ACCNO")

        self.account_num = account_list.split(';')[0]

        print("나의 보유 계좌번호 %s" % self.account_num)#8034722411

    def detail_account_info(self):
        print("예수금 요청오는 부분")

        self.dynamicCall("SetInputValue(String, String)","계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(String, String)","비밀번호", "0000")
        self.dynamicCall("SetInputValue(String, String)","비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(String, String)","조회구분", "2")
        self.dynamicCall("CommRqData(String, String, int, String)", "예수금상세현황요청", "opw00001", "0", self.screen_my_info)

        self.detail_account_info_event_loop = QEventLoop()
        self.detail_account_info_event_loop.exec_()
    
    def detail_account_mystock(self, sPrevNext = '0'):
        print("계좌평가 잔고내역 요청하기 연속조회 %s" %sPrevNext)
        
        self.dynamicCall("SetInputValue(String, String)","계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(String, String)","비밀번호", "0000")
        self.dynamicCall("SetInputValue(String, String)","비밀번호입력매체구분", "00")
        self.dynamicCall("SetInputValue(String, String)","조회구분", "2")
        self.dynamicCall("CommRqData(String, String, int, String)", "계좌평가잔고내역요청", "opw00018", sPrevNext, self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    def not_concluded_account(self, sPreNext = "0"): ##미체결 주식
        self.dynamicCall("SetInputValue(QString, QString)","계좌번호", self.account_num)
        self.dynamicCall("SetInputValue(QString, QString)","체결구분", "1")
        self.dynamicCall("SetInputValue(QString, QString)","매매구분", "0")
        self.dynamicCall("CommRqData(QString, QString, int, QString)", "실시간미체결요청", "opt10075", sPreNext, self.screen_my_info)

        self.detail_account_info_event_loop.exec_()

    def get_code_list_by_market(self, market_code):
        '''종목 코드들 반환'''
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market_code)
        code_list = code_list.split(";")[:-1]

        return code_list
    
    def calculator_fnc(self):
        code_list = self.get_code_list_by_market("10")
        print("코스닥 갯수 %s" %len(code_list))

        for idx, code in enumerate(code_list):

            self.dynamicCall("DisconnectRealDate(QString)",self.screen_calculation_stock)

            print("%s / %s : KOSDAQ Stock Code : is %s is updating ..... " % ((idx+1), len(code_list), code))

            self.day_kiwoom_db(code = code)
    
    def day_kiwoom_db(self, code = None, date = None, sPrevNext = "0"):#주식일봉차트조회

        QTest.qWait(3600) 

        self.dynamicCall("SetInputValue(Qstring, Qstring)","종목코드", code)
        self.dynamicCall("SetInputValue(Qstring, Qstring)","수정주가구분", "1")

        if date != None:
            self.dynamicCall("SetInputValue(Qstring, Qstring)","기준일자", date)

        self.dynamicCall("CommRqData(QString, QString, int, QString)", "주식일봉차트조회", "opt10081", sPrevNext, self.screen_calculation_stock)    

        self.calculator_event_loop.exec_()

    def trdata_slot(self, sScrNo, sRQName, sTrCode, sRecordName, sPreNext): #sPreNext: "0" "2" 값을 가진다
        '''
        tr 요청을 받는 구역 
        sScrNo: 스크린번호
        sRQName: 내가 요청했을 때 지은 이름
        sTrCode: 요청id, tr 코드
        sPrevNext: 다음 페이지가 있는지 
        '''

        if sRQName == "예수금상세현황요청":
            deposit = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, "예수금")
            print("예수금 %s" % type(deposit))
            print("예수금 형변환 %s"%int(deposit))

            self.use_money = int(deposit) * self.use_money_percent
            self.use_money = self.use_money / 4

            ok_deposit = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, "출금가능금액")
            print("출금가능금액 %s" % type(ok_deposit))
            print("출금가능금액 형변환 %s" % int(ok_deposit))

            self.detail_account_info_event_loop.exit()
        
        elif sRQName == "계좌평가잔고내역요청":

            total_buy_money = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, "총매입금액")
            total_buy_money_result = int(total_buy_money)

            print("총매입금액 %s" % total_buy_money_result)

            total_profit_loss_rate = self.dynamicCall("GetCommData(String, String, int, String)", sTrCode, sRQName, 0, "총수익률(%)")
            total_profit_loss_rate_result = float(total_profit_loss_rate)
            print("총수익률(%%) : %s" % total_profit_loss_rate_result)


            rows = self.dynamicCall("GetRepeatCnt(Qstring, Qstring)", sTrCode, sRQName) #보유 종목 20개만 먼저 보여줌
            cnt = 0

            for i in range(rows):
                code = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "종목번호")
                code = code.strip()[1:] # A2310 -> 2310

                code_nm = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "종목명")
                stock_quantity = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "보유수량")
                buy_price = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "매입가")
                learn_rate = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "수익률(%)")
                current_price = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "현재가")
                total_chegual_price = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "매입금액")
                possible_quantity = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "매매가능수량")

                if code in self.account_stock_dict:
                    pass
                else:
                    self.account_stock_dict.update({code:{}})

                code_nm = code_nm.strip()
                stock_quantity = int(stock_quantity.strip())
                buy_price = int(buy_price.strip())
                learn_rate = float(learn_rate.strip())
                current_price = int(current_price.strip())
                total_chegual_price = int(total_chegual_price.strip())
                possible_quantity = int(possible_quantity.strip())

                self.account_stock_dict[code].update({"종목명": code_nm})
                self.account_stock_dict[code].update({"보유수량": stock_quantity})
                self.account_stock_dict[code].update({"매입가": buy_price})
                self.account_stock_dict[code].update({"수익률(%)": learn_rate})
                self.account_stock_dict[code].update({"현재가": current_price})
                self.account_stock_dict[code].update({"매입금액": total_chegual_price})
                self.account_stock_dict[code].update({"매매가능수량": possible_quantity})
                #{"02039": {"종목명": "어디", "보유수량": 몇개 ....}}
                cnt += 1
                 
            print("계좌에 가지고 있는 종목 %s" % self.account_stock_dict)
            print("계좌에 보유종목 카운트 %s" % cnt)

            if sPreNext == "2": #보유종목이 20개가 넘으면 sPreNext = 2 로 요청!
                self.detail_account_mystock(sPrevNext="2")
            else:
                self.detail_account_info_event_loop.exit()
        
        elif sRQName == "실시간미체결요청":

            rows = self.dynamicCall("GetRepeatCnt(Qstring, Qstring)", sTrCode, sRQName)

            for i in range(rows):
                code = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "종목코드")
                code_nm = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "종목명")
                order_no = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "주문번호")
                order_status = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "주문상태")

                # 접수 -> 확인 -> 체결

                order_quantity = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "주문수량")
                order_price = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "주문가격")
                order_gubun = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "주문구분") #+매수 , -매도
                not_quantity = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "미체결수량")
                ok_quantity = self.dynamicCall("GetCommData(Qstring, Qstring, int, Qstring)",sTrCode, sRQName, i, "체결량")

                code = code.strip()
                code_nm = code_nm.strip()
                order_no = int(order_no.strip())
                order_status = order_status.strip()
                order_quantity = int(order_quantity.strip())
                order_price = int(order_price.strip())
                order_gubun = order_gubun.strip().lstrip('+').lstrip('-') #"-매도","+매수"
                not_quantity = int(not_quantity.strip())
                ok_quantity = int(ok_quantity.strip())


                if order_no in self.not_account_stock_dict:
                    pass
                else:
                    self.not_account_stock_dict[order_no] = {}

                

                self.not_account_stock_dict[order_no].update({"종목코드" : code})
                self.not_account_stock_dict[order_no].update({"종목명" : code_nm})
                self.not_account_stock_dict[order_no].update({"주문번호" : order_no})
                self.not_account_stock_dict[order_no].update({"주문상태" : order_status})
                self.not_account_stock_dict[order_no].update({"주무수량" : order_quantity})
                self.not_account_stock_dict[order_no].update({"주문가격" : order_price})
                self.not_account_stock_dict[order_no].update({"주문구분" : order_gubun})
                self.not_account_stock_dict[order_no].update({"미체결수량" : not_quantity})
                self.not_account_stock_dict[order_no].update({"체결량" : ok_quantity})

                print("미체결 종목: %s " % self.not_account_stock_dict[order_no])
            
            self.detail_account_info_event_loop.exit()

        elif sRQName == "주식일봉차트조회":

            code = self.dynamicCall("GetCommData(QString,QString,int,QString)",sTrCode, sRQName, 0, "종목코드")
            code = code.strip()
            print("%s 일봉 데이터 요청" % code)

            cnt = self.dynamicCall("GetRepeatCnt(QString, Qstring)", sTrCode, sRQName)
            print("데이터 일수 %s" % cnt)

            #data = self.dynamicCall("GetCommData(QString,QString,int,QString)",sTrCode, sRQName)
            #[['','현재가','거래량','거래대금','날짜','시가','고가','저가',''],['','현재가',....]

            #한번 조회하면 600일차 까지 일봉데이터를 받아 올 수 있다

            for i in range(cnt): #for문을 통해 하루하루씩 가져오고 있다
                data = []

                current_price = self.dynamicCall("GetCommData(QString,QString,int,QString)",sTrCode, sRQName, 0, "현재가")
                value = self.dynamicCall("GetCommData(QString,QString,int,QString)",sTrCode, sRQName, 0, "거래량")
                trading_value = self.dynamicCall("GetCommData(QString,QString,int,QString)",sTrCode, sRQName, 0, "거래대금")
                date = self.dynamicCall("GetCommData(QString,QString,int,QString)",sTrCode, sRQName, 0, "일자")
                start_price = self.dynamicCall("GetCommData(QString,QString,int,QString)",sTrCode, sRQName, 0, "시가")
                high_price = self.dynamicCall("GetCommData(QString,QString,int,QString)",sTrCode, sRQName, 0, "고가")
                low_price = self.dynamicCall("GetCommData(QString,QString,int,QString)",sTrCode, sRQName, 0, "저가")

                data.append("")
                data.append(current_price.strip())
                data.append(value.strip())
                data.append(trading_value.strip())
                data.append(date.strip())
                data.append(start_price.strip())
                data.append(high_price.strip())
                data.append(low_price.strip())
                data.append("")

                self.calcul_data.append(data.copy())

            print(len(self.calcul_data))

            # 주식 종합 차트

            if sPreNext == "2":
                self.day_kiwoom_db(code = code, sPrevNext= sPreNext)
            else:
                print("총 일수 %s" % len(self.calcul_data))

                pass_success = False

                #120일 이평선을 그릴만큼의 데이터가 있는 지 체크
                if self.calcul_data == None or len(self.calcul_data) < 120:
                    pass_success = False
                else:
                    #120일 이상 되면
                    total_price = 0
                    for value in self.calcul_data[:120]:
                        total_price += int(value[1])

                    moving_average_price = total_price / 120

                    #오늘자 주가가 120일 이평선에 걸쳐있는지 확인
                    bottom_stock_price = False
                    check_price = None
                    if int(self.calcul_data[0][7]) <= moving_average_price and moving_average_price <= int(self.calcul_data[0][6]):
                        print("오늘 주가가 120이평선에 걸쳐 있는 것 확인")
                        bottom_stock_price = True
                        check_price = int(self.calcul_data[0][6])

                    #과거 일봉들이 120일 이평선보다 밑에 있는지 확인
                    #그렇게 확인을 하다가 일봉이 120일 이평선보다 위에 있으면 계산 진행
                    prev_price = None #과거의 일봉 저가
                    if bottom_stock_price == True:

                        moving_average_price = 0
                        price_top_moving = False
                        
                        idx = 1
                        while True:

                            if len(self.calcul_data[idx:]) < 120: #120일치가 있는지 계속 확인
                                print("120일치가 없음!")
                                break

                            total_price = 0
                            for value in self.calcul_data[idx:120+idx]:
                                total_price += int(value[1])
                            moving_average_price_prev = total_price / 120

                            if moving_average_price_prev <= int(self.calcul_data[idx][6]) and idx <= 20:
                                print("20일 동안 주가가 120일 이평선과 같거나 위에 있으면 조건 통과 못함")
                                price_top_moving = False
                                break
                            elif int(self.calcul_data[idx][7]) > moving_average_price_prev and idx >20:
                                print("120일 이평선 위에 있는 일봉 확인됨")
                                price_top_moving = True
                                prev_price = int(self.calcul_data[idx][7])
                                break
                            idx += 1

                        #해당 부분 이평선이 가장 최근 일자의 이평선 가격보다 낮은지 확인
                        if price_top_moving == True:
                            if moving_average_price > moving_average_price_prev and check_price > prev_price:
                                print("포착된 이평선의 가격이 오늘자(최근일자) 이평선 가격보다 낮은 것 확인됨")
                                print("포착된 부분의 일봉 저가가 오늘자 일봉의 고가보다 낮은지 확인됨")
                                pass_success = True 
                        
                if pass_success == True:
                    print("조건부 통과됨")
                    
                    code_nm = self.dynamicCall("GetMasterCodeName(QString)",code)

                    f = open("files/condition_stock.txt","a",encoding="utf8")
                    f.write("%s %s %s\n" % (code, code_nm, str(self.calcul_data[0][1])))
                    f.close()

                elif pass_success == False:
                    print("조건부 통과 못함")
                
                self.calcul_data.clear()
                self.calculator_event_loop.exit()



    def read_code(self):

        if os.path.exists("files/condition_stock.txt"):

            f = open("files/condition_stock.txt","r", encoding = 'utf8')

            lines = f.readlines()

            for line in lines:
                if line != "":
                    ls = line.split(" ")
                    
                    stock_code = ls[0]
                    stock_name = ls[1]
                    stock_price = int(ls[2].split("\n")[0])
                    stock_price = abs(stock_price)

                    self.portfolio_stock_dict.update({stock_code: {"종목명": stock_name, "현재가": stock_price}})
            
            f.close()

            print(self.portfolio_stock_dict)

    def screen_number_setting(self):

        screen_overwrite = []

        for code in self.account_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        for order_number in self.not_account_stock_dict.keys():
            code = self.not_account_stock_dict[order_number]['종목코드']


            if code not in screen_overwrite:
                screen_overwrite.append(code)

        for code in self.portfolio_stock_dict.keys():
            if code not in screen_overwrite:
                screen_overwrite.append(code)

        cnt = 0
        for code in screen_overwrite:

            temp_screen = int(self.screen_real_stock)
            meme_screen = int(self.screen_meme_stock)

            if (cnt % 50) == 0:
                temp_screen += 1
                self.screen_real_stock = str(temp_screen)
            
            if (cnt % 50) == 0:
                meme_screen += 1
                self.screen_meme_stock = str(meme_screen)
            
            if code in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict[code].update({"스크린번호": str(self.screen_real_stock)})
                self.portfolio_stock_dict[code].update({"주문용스크린번호": str(self.screen_meme_stock)})
            
            elif code not in self.portfolio_stock_dict.keys():
                self.portfolio_stock_dict.update({code:{"스크린번호": str(self.screen_real_stock),"주문용스크린번호": str(self.screen_meme_stock)}})

            cnt += 1
        print(self.portfolio_stock_dict) 

    def realdata_slot(self, sCode, sRealType, sRealData):

        if sRealType == "장시작시간":
            fid = self.realType.REALTYPE[sRealType]['장운영구분']
            value = self.dynamicCall("GetCommRealData(QString,int)", sCode, fid)

            if value == "0":
                print("장 시작 전")
            elif value == "3":
                print("장 시작")
            elif value == "2":
                print("장 종료, 동시호가로 넘어감")
            elif value == "4":
                print("3시 30분 장 종료")

                for code in self.portfolio_stock_dict.keys():
                    self.dynamicCall("SetRealRemove(String, String)", self.portfolio_stock_dict[code]['스크린번호'])

                QTest.qWait(5000)

                self.file_delete()
                self.calculator_fnc()

                sys.exit()

        elif sRealType == "주식체결":
            a = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['체결시간']) #HHMMSS
            b = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['현재가']) #+(-)22500
            b = abs(int(b))

            c = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['전일대비'])
            c = abs(int(c))

            d = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['등락율'])
            d = float(d)

            e = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['(최우선)매도호가'])
            e = abs(int(e))

            f = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['(최우선)매수호가'])
            f = abs(int(f))

            g = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['거래량'])
            g = abs(int(g))

            h = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['누적거래량'])
            h = abs(int(h))
            
            i = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['고가'])
            i = abs(int(i))

            j = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['시가'])
            j = abs(int(j))

            k = self.dynamicCall("GetCommRealData(QString, int)", sCode, self.realType.REALTYPE[sRealType]['저가'])
            k = abs(int(k))

            if sCode not in self.portfolio_stock_dict:
                self.portfolio_stock_dict.update({sCode:{}})

            self.portfolio_stock_dict[sCode].update({"체결시간":a})
            self.portfolio_stock_dict[sCode].update({"현재가":b})
            self.portfolio_stock_dict[sCode].update({"전일대비":c})
            self.portfolio_stock_dict[sCode].update({"등락율":d})
            self.portfolio_stock_dict[sCode].update({"(최우선)매도호가":e})
            self.portfolio_stock_dict[sCode].update({"(최우선)매수호가":f})
            self.portfolio_stock_dict[sCode].update({"거래량":g})
            self.portfolio_stock_dict[sCode].update({"누적거래량":h})
            self.portfolio_stock_dict[sCode].update({"고가":i})
            self.portfolio_stock_dict[sCode].update({"시가":j})
            self.portfolio_stock_dict[sCode].update({"저가":k})

            print(self.portfolio_stock_dict[sCode])

            #계좌잔고평가내역에 있고 오늘 산 잔고에는 없을 경우
            if sCode in self.account_stock_dict.keys() and sCode not in self.jango_dict.keys():
                print("%s %s" %("신규매도를 한다", sCode))

                asd = self.account_stock_dict[sCode]

                meme_rate = (b - asd['매입가']) / asd['매입가'] * 100

                if asd['매매가능수량'] > 0 and (meme_rate > 5 or meme_rate < -5):
                    order_success = self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                                        ["신규매도", self.portfolio_stock_dict[sCode]['주문용스크린번호'], self.account_num, 2,
                                        sCode, asd['매매가능수량'], 0, self.realType.SENDTYPE['거래구분']['시장가'],""])

                    if order_success == 0:
                        print("매도주문 전달 성공")
                        del self.account_stock_dict[sCode]
                    else:
                        print("매도주문 전달 실패")

            #오늘 산 잔고에 있을 경우
            elif sCode in self.jango_dict.keys():
                jd = self.jango_dict[sCode]
                meme_rate = (b - jd['매입단가']) / jd['매입단가'] * 100

                if jd['주문가능수량'] > 0 and (meme_rate > 5 or meme_rate < -5):

                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)"
                        ["신규매도", self.portfolio_stock_dict[sCode]["주문용스크린번호"],self.account_num,2,sCode,jd['주문가능수량'],
                        0, self.realType.SENDTYPE['거래구분']['시장가'],""]
                    )

                    if order_success == 0:
                        self.logging.logger.debug("매도주문 전달 성공")
                        
                    else:
                        self.logging.logger.debug("매도주문 전달 실패")
            
            #등락율이 2.0% 이상이고 오늘 산 잔고에 없을 경우
            elif d > 2.0 and sCode not in self.jango_dict:
                print("%s %s" % ("신규매수를 한다", sCode))

                result = (self.use_money * 0.1) / e
                quantity = int(result)

                order_success = self.dynamicCall(
                    "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                    ["신규매수", self.portfolio_stock_dict[sCode]["주문용스크린번호"],self.account_num, 1, sCode, quantity, e, self.realType.SENDTYPE['거래구분']['지정가'],""]
                )

                if order_success == 0:
                    self.logging.logger.debug("매수주문 전달 성공")
                else:
                    self.logging.logger.debug("매수주문 전달 실패")
            
            #취소주문..
            not_meme_list = list(self.not_account_stock_dict)
            
            for order_num in not_meme_list:
                code = self.not_account_stock_dict[order_num]["종목코드"]
                meme_price = self.not_account_stock_dict[order_num]["주문가격"]
                not_quantity = self.not_account_stock_dict[order_num]['미체결수량']
                order_gubun = self.not_account_stock_dict[order_num]['주문구분']

                if order_gubun == "매수" and not_quantity > 0 and e > meme_price:
                    order_success = self.dynamicCall(
                        "SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                        ["매수취소", self.portfolio_stock_dict[sCode]["주문용스크린번호"],self.account_num, 3, code, 0, 0,
                        self.realType.SENDTYPE['거래구분']['지정가'], order_num]
                    )

                    if order_success == 0:
                        self.logging.logger.debug("매수주문 전달 성공")
                    else:
                        self.logging.logger.debug("매수주문 전달 실패")

                elif not_quantity == 0:
                    del self.not_account_stock_dict[order_num]

    def chejan_slot(self, sGubun, nItemCnt, sFIdList):

        if int(sGubun) == 0:

            account_num = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['계좌번호'])
            sCode = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['종목코드'])[1:]
            stock_name = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['종목명'])
            stock_name = stock_name.strip()

            origin_order_number = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['원주문번호'])
            order_number = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문번호'])
            order_status = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문상태'])
            order_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문수량'])
            order_quan = int(order_quan)

            order_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문가격'])
            order_price = int(order_price)

            not_chegual_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['미체결수량'])
            not_chegual_quan = int(not_chegual_quan)

            order_gubun = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문구분'])
            order_gubun = order_gubun.strip().lstrip('+').lstrip('-')

            chegual_time_str = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['주문/체결시간'])
            
            chegual_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['체결가'])

            if chegual_price == "":
                chegual_price = 0
            else:
                chegual_price = int(chegual_price)

            chegaul_quantity = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['체결량'])

            if chegaul_quantity == "":
                chegaul_quantity = 0
            else:
                chegaul_quantity = int(chegaul_quantity)

            current_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['현재가'])
            current_price = abs(int(current_price))

            first_sell_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['(최우선)매도호가'])
            first_sell_price = abs(int(first_sell_price))

            first_buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['주문체결']['(최우선)매수호가'])
            first_buy_price = abs(int(first_buy_price))

            if order_number not in self.not_account_stock_dict.keys():
                self.not_account_stock_dict.update({order_number: {}})

            self.not_account_stock_dict[order_number].update({"종목코드": sCode})
            self.not_account_stock_dict[order_number].update({"주문번호": order_number})
            self.not_account_stock_dict[order_number].update({"종목명": stock_name})
            self.not_account_stock_dict[order_number].update({"주문상태": order_status})
            self.not_account_stock_dict[order_number].update({"주문수량": order_quan})
            self.not_account_stock_dict[order_number].update({"주문가격": order_price})
            self.not_account_stock_dict[order_number].update({"미체결수량": not_chegual_quan})
            self.not_account_stock_dict[order_number].update({"원주문번호": origin_order_number})
            self.not_account_stock_dict[order_number].update({"주문구분": order_gubun})
            self.not_account_stock_dict[order_number].update({"주문/체결시간": chegual_time_str})
            self.not_account_stock_dict[order_number].update({"체결가": chegual_price})
            self.not_account_stock_dict[order_number].update({"체결량": chegaul_quantity})
            self.not_account_stock_dict[order_number].update({"현재가": current_price})
            self.not_account_stock_dict[order_number].update({"(최우선)매도호가": first_sell_price})
            self.not_account_stock_dict[order_number].update({"(최우선)매수호가": first_buy_price})
            
            print(self.not_account_stock_dict)

        elif int(sGubun) == 1:

            account_num = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['계좌번호'])
            sCode = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['종목코드'])[1:]

            stock_name = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['종목명'])
            stock_name = stock_name.strip()
             
            current_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['현재가'])
            current_price = abs(int(current_price))

            stock_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['보유수량'])
            stock_quan = int(stock_quan)

            like_quan = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['주문가능수량'])
            like_quan = int(like_quan)

            buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['매입단가'])
            buy_price = abs(int(buy_price))

            #total_buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['총매입가(당일누적)'])
            #total_buy_price = int(total_buy_price)

            meme_gubun = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['매도매수구분'])
            meme_gubun = self.realType.REALTYPE['매도수구분'][meme_gubun]

            first_sell_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['(최우선)매도호가'])
            first_sell_price = abs(int(first_sell_price))

            first_buy_price = self.dynamicCall("GetChejanData(int)", self.realType.REALTYPE['잔고']['(최우선)매수호가'])
            first_buy_price = abs(int(first_buy_price))

            if sCode not in self.jango_dict.keys():
                self.jango_dict.update({sCode: {}})

                self.jango_dict[sCode].update({"현재가": current_price})
                self.jango_dict[sCode].update({"종목코드": sCode})
                self.jango_dict[sCode].update({"종목명": stock_name})
                self.jango_dict[sCode].update({"보유수량": stock_quan})
                self.jango_dict[sCode].update({"주문가능수량": like_quan})
                self.jango_dict[sCode].update({"매입단가": buy_price})
                #self.jango_dict[sCode].update({"총매입가(당일누적)": total_buy_price})
                self.jango_dict[sCode].update({"매도매수구분": meme_gubun})
                self.jango_dict[sCode].update({"(최우선)매도호가": first_sell_price})
                self.jango_dict[sCode].update({"(최우선)매수호가": first_buy_price})


                if stock_quan == 0:
                    del self.jango_dict[sCode]
                    self.dynamicCall("setRealRemove(QString,QString)",self.portfolio_stock_dict[sCode]['스크린번호'],sCode)
        

        #송수신 메세지 get
    def msg_slot(self, sScrNO, sRQName, sTrCode, msg):
        print("스크린: %s, 요청이름: %s, tr코드: %s --- %s" % (sScrNO, sRQName, sTrCode, msg))


    def file_delete(self):
        if os.path.isfile("files/condition_stock.txt"):
            os.remove("files/condition_stock.txt")
