__author__ = 'jarethmoyo'
#If there is no schedule.txt file, for the optimization lib to work, we have to create one, though empty
gin=open('schedule.txt','w')

import urllib2
from bs4 import BeautifulSoup
from Tkinter import *
import optimization
import re
from operator import itemgetter
from tkMessageBox import *

days=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
#First capture the Course Code
regEx=r'([A-Z]+\s+\d+\s*[A-Z0-9]*\s*\d*)'
#capture everything and split with id
divider=re.compile(regEx)
#Regular expression to capture timings
reg4d=r'(\d{2}:\d{2})-(\d{2}:\d{2})'
#Regular expression to capture departmental codes
depReg=r'[A-Z]+'


class MainEngine:
    def __init__(self,url):
        self.url =url
        self.course_classes={}  # will contain departmental codes as keys and courses in that department as values
        self.course_dict={}  # will contain course ids as keys, and details about the courses as values

    def fetch(self):
        c=urllib2.urlopen(self.url)
        soup=BeautifulSoup(c.read())
        d=soup.find_all('div',{'class':'article article-body'})
        d2= d[0].text.strip().split('\n')
        d3=[x.strip() for x in d2 if x != '']
        delimeter='??'
        d4=delimeter.join(d3)
        d5=d4.split('Member(s)??')
        d5=d5[1] # d5 is the string with all the data stored in it
        raw_data=divider.split(d5)
        raw_data=raw_data[1:] # ignore the first element in the list
        course_dict={} # will contain course ids as keys, and details about the courses as values
        course_classes={} # will contain departmental courses as keys and the courses in that dep as values
        for i in range(1,len(raw_data),2):
            details=[x for x in raw_data[i].split('??') if x!='']
            #To correct the problem involving attached days
            c=0
            for item in details:
                for day in days:
                    if day in item and len(item)>12:
                        temp=item.split()
                        details.remove(item)
                        for el in temp[::-1]:
                            details.insert(c,el)
                        break
                c+=1
            course_days=[y for y in details if y in days]  # on which days the course takes place
            course_name=''
            course_times=[z for z in details if re.match(reg4d,z)]  # timings of the course
            if len(course_days)==0 or len(course_times)==0:
                continue
            else:
                for j in range(len(details)):
                    if details[j] not in days:
                        course_name+=' '+details[j]
                    else:
                        break
                course_dict[raw_data[i-1]]=[course_name,course_days,course_times]
        for item in course_dict.keys():
            depcode=re.match(depReg,item).group(0)
            if depcode not in course_classes:
                course_classes[depcode]=[item]
            else:
                course_classes[depcode].append(item)

        self.course_dict=course_dict
        self.course_classes=course_classes
        return self.course_dict,self.course_classes

    def calculatesol(self,vec):
        #list_of_courses=self.course_classes['MATH']
        slots=[]
        for i in range(len(list_of_courses)): slots+=[i]
        all_data=[['Sunday','No Classes'],['Monday','No Classes'],['Tuesday','No Classes'],
            ['Wednesday','No Classes'],['Thursday','No Classes'],['Friday','No Classes'],['Saturday','No Classes']]
        for i in range(len(vec)):
            x=int(vec[i])
            course=list_of_courses[slots[x]]
            title=self.course_dict[course][0]  # Title of the course
            dates=self.course_dict[course][1]  # Days in which the course can be taken
            times=self.course_dict[course][2]  # Times at which the course can be taken
            for j in range(len(all_data)):
                curr_day=all_data[j][0]
                curr_sch=all_data[j][1]
                if curr_day in dates:
                    if curr_sch == 'No Classes':
                        for index,value in enumerate(dates): # loop through all the dates in each course
                            if value == curr_day:
                                all_data[j][1]=(times[index],title)
                    else:
                        for index,value in enumerate(dates):
                            if value == curr_day:
                                all_data[j][1]+=(times[index],title)
            del slots[x]
        return all_data

    def cost_func(self,vec):
        cost=0 # this is the initial cost
        output=self.calculatesol(vec)
        data_dict={}  # will contain data in a useful format
        sorted_data={}  # will contain data in sorted format
        for item,value in output:
            data_dict.setdefault(item,[])
            if value=='No Classes': continue # ignore dates with no classes
            for i in range(1,len(value),2):
                times=value[i-1]
                subject=value[i]
                # get the times by using the regular expression defined earlier
                timestart=re.search(reg4d,times).group(1)
                timeend=re.search(reg4d,times).group(2)
                time_1=optimization.getminutes(timestart)  # timestart converted to minutes
                time_2=optimization.getminutes(timeend)  # timeend converted to minutes
                data_dict[item].append((subject,time_1,time_2))
        # now to sort values in the dictionary data_dict
        for ele,val in data_dict.items():
            temp=sorted(val,key=itemgetter(1))
            sorted_data[ele]=temp
        for cday,dlist in sorted_data.items():
            if len(dlist)==0:
                if cday=='Monday' or cday=='Friday':
                    cost-=2000
                else:
                    cost-=1000
                continue
            break_cost=[]  # this is for the cost of the breaks
            #traversing through every course on each day
            for i in range(len(dlist)):
                init_time_pr=dlist[i][1]  # the time at which the preceding course starts
                end_time_pr=dlist[i][2]  # the time at which the preceding course ends
                for j in range(i+1,len(dlist)):
                    init_time_nxt=dlist[j][1]  # the time at which the next course starts
                    end_time_nxt=dlist[j][2]  # the time at which the next course ends
                    #the formula we will use to calculate time conflicts is illustrated below
                    max_of_initial=max(init_time_pr,init_time_nxt)  # maximum of the two initial times
                    min_of_final=min(end_time_pr,end_time_nxt)  # minimum of the end times
                    diff = min_of_final-max_of_initial
                    #if diff is negative, the are no time clashes. else, there is a time clash
                    if diff<0:  # no time clash
                        continue
                    else:
                        cost+=diff*1000
            # now to calculate break costs
            for k in range(1,len(dlist)):
                end=dlist[k-1][2]  # end of previous course
                start=dlist[k][1]  # start of next course
                if start-end > 0:  # no clashes and there is a break:
                    break_cost.append(start-end)
            if len(break_cost)>=1:
                total_breaks=reduce(lambda x,y: x*y,break_cost)/1000  # to calculate total break cost
                cost+= total_breaks

        return cost


class App(object):
    def __init__(self,master):
        master.title('A JCK PRODUCTION')
        frame1= Frame(master)
        frame1.pack()
        frame6=Frame(master)
        frame6.pack()
        frame2=Frame(master)
        frame2.pack(anchor=W)
        frame5=Frame(frame2)
        frame5.pack(anchor=W,side=LEFT)
        frame3=Frame(master)
        frame3.pack(anchor=W)
        frame4=Frame(master)
        frame4.pack(anchor=W)
        self.flag=1
        L1=Label(frame1, text='Course Schedule Advisor', bg='green',fg='White',width=40,font='Helvetica 25 bold')
        L1.pack()
        L2=Label(frame1,text='Provide Course Offerings URL:',font='Times 15 bold')
        L2.pack(anchor=W,pady=5,padx=15)
        self.T1=Text(frame1, width=50, height=1,font='Veronica 15')
        self.T1.pack(side=LEFT,padx=18,pady=5)
        self.B1=Button(frame1,text='Fetch Course\nOfferings',font='Helvetica 12',width=20,fg='Blue',
                       command=self.fetch_courses)
        self.B1.pack(pady=5)
        L3=Label(frame6,text='\/'*80,fg='white',bg='lightgreen')
        L3.pack()
        L4=Label(frame5,text='Select\nCourse\nCodes',font='Times 12 bold')
        L4.pack(anchor=N,side=LEFT,pady=5)
        self.lb=Listbox(frame5, width=25,selectmode=MULTIPLE)
        scroll_1=Scrollbar(frame5,command=self.lb.yview)
        scroll_1.pack(side=RIGHT,fill=Y)
        self.lb.config(yscrollcommand=scroll_1.set)
        self.lb.pack(side=LEFT,pady=10,padx=10)
        L5=Label(frame2,text='Provide the\nNumber of\nCourses:',font='Times 12 bold')
        L5.pack(anchor=N,side=LEFT,padx=20)
        self.T2=Text(frame2,width=2,height=1,font='Veronica 12')
        self.T2.pack(anchor=N,side=LEFT,pady=20)
        L6=Label(frame2,text='Choose the\noptimization\nmethod:',font='Times 12 bold')
        L6.pack(anchor=N,side=LEFT,padx=40)
        L7=Label(frame2,text='..........\n'*9,font='Veronica 10 italic',fg='blue').pack(side=LEFT,anchor=N)
        #radio button settings
        self.v=IntVar()
        self.v.set(1)
        self.rb1=Radiobutton(frame2,text='Hill Climbing              .',variable=self.v,value=1,
                             command=self.hill_opt)
        self.rb1.pack(anchor=N)
        self.rb2=Radiobutton(frame2,text='Simulated Annealing  ',variable=self.v,value=2,
                             command=self.annealing_opt)
        self.rb2.pack()
        self.rb3=Radiobutton(frame2,text='Genetic Optimization  ',variable=self.v,value=3,
                             command=self.genetic_opt)
        self.rb3.pack()
        self.rb4=Radiobutton(frame2,text='Random Optimization',variable=self.v,value=4,
                             command=self.random_opt)
        self.rb4.pack()
        self.B2=Button(frame3,text='Create Course Schedule',width=25,font='Helvetica 15',fg='Blue',
                       command=self.create_course_schedule)
        self.B2.pack(padx=20,pady=10,side=LEFT)
        self.T3=Text(frame4,width=87,height=14,font='Veronica 12',fg='blue')
        scroll_2=Scrollbar(frame4,command=self.T3.yview)
        scroll_2.pack(side=RIGHT,fill=Y)
        self.T3.config(yscrollcommand=scroll_2.set)
        self.T3.pack(pady=10)

    def fetch_courses(self):
        url_input=self.T1.get('1.0','end-1c')
        try:
            self.fetcher=MainEngine(url_input)
            res=self.fetcher.fetch()
            self.main_dict=res[0]  # the main dictionary with information about each course
            self.dep_dict=res[1]  # the departmental code dictionary, same as self.course_classes
            dep_codes=self.dep_dict.keys()
            dep_codes.sort()
            #Now to populate the listbox
            for item in dep_codes:
                self.lb.insert(END, item)
        except:
            showerror('Operational Error',
                      message='An Error has occured. Either:\n1)Your Url is invalid.\n2)Internet connection was lost')

    def create_course_schedule(self):
        global list_of_courses
        dcodes = [self.lb.get(x) for x in self.lb.curselection()]  # department codes
        list_of_courses=[]  # list of courses, will be populated from dep codes
        for item in dcodes:
            info=self.dep_dict[item]
            for el in info:
                list_of_courses.append(el)
        #csol=self.fetcher.calculatesol([0]*16) # just a test solution
        num_of_courses=self.T2.get('1.0','end-1c')  # These are the number of courses selected by student
        if len(num_of_courses)==0:
            showerror('An Error has Occured',message='Please input the number of courses you wish to take')
        else:
            self.domain=[(0,int(num_of_courses)-i-1) for i in range(0,int(num_of_courses))]
            self.vec=self.select_opt_method()
            csol=self.fetcher.calculatesol(self.vec)  # this is the solution to print out, in unsorted format
            # Now to sort the format of the csol in a clearer representation
            sorted_sched=[]
            for day,sched in csol:
                if sched=='No Classes':
                    sorted_sched.append((day,sched))  # we can't do much with these
                else:
                    temp=[]
                    sorted_class=()
                    for i in range(1,len(sched),2):
                        if int(sched[i-1][0])==0:
                            tim = int(sched[i-1][1])
                        else:
                            tim=sched[i-1][0:2]  # timings which we will sort by
                            tim=int(tim)

                        temp.append(tim)
                    temp.sort()
                    for sorter in temp:
                        for i in range(1,len(sched),2):
                            if int(sched[i-1][0])==0:
                                tim2 = int(sched[i-1][1])
                            else:
                                tim2=sched[i-1][0:2]  # timings which we will sort by
                                tim2=int(tim2)
                            if tim2 == sorter:
                                if sched[i] not in sorted_class: # only then shall we add to the reorganized tuple
                                    sorted_class+=(sched[i-1],sched[i])
                                else:
                                    continue
                    sorted_sched.append((day,sorted_class))
            self.T3.delete('1.0',END)
            for cday,clas in sorted_sched:
                self.T3.insert(END,'%s:\n %s\n\n'%(cday,clas))

    # these functions are for choosing the optimization method to use
    def select_opt_method(self):
        print self.flag
        if self.flag==1:
            return optimization.hillclimb(self.domain,self.fetcher.cost_func)
        elif self.flag==2:
            return optimization.annealingoptimize(self.domain,self.fetcher.cost_func)
        elif self.flag==3:
            return optimization.geneticoptimize(self.domain,self.fetcher.cost_func)
        else:
            return optimization.randomoptimize(self.domain,self.fetcher.cost_func)

    def hill_opt(self):
        self.flag =1

    def annealing_opt(self):
        self.flag=2

    def genetic_opt(self):
        self.flag=3

    def random_opt(self):
        self.flag=4





root=Tk()
app=App(root)
root.mainloop()


