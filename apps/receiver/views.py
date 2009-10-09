from django.http import HttpResponse, HttpResponseServerError, HttpResponseBadRequest
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext
from django.core.exceptions import *
from rapidsms.webui.utils import render_to_response
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.utils.translation import ugettext_lazy as _
from django.db.models.query_utils import Q
from django.core.urlresolvers import reverse
from xformmanager.manager import XFormManager
# this import is just so we can get StorageUtility.XFormError
from xformmanager.storageutility import StorageUtility
from transformers.zip import get_zipfile

from datetime import timedelta, datetime
from django.db import transaction
import mimetypes

from receiver.models import *
from receiver.models import _XFORM_URI as XFORM_URI
from receiver.submitresponse import SubmitResponse
from django.contrib.auth.models import User

from hq.utils import paginate
from hq.decorators import extuser_required

import logging
import hashlib
import traceback
import sys
import os
import string
import submitprocessor


@extuser_required()
def show_dupes(request, submission_id, template_name="receiver/show_dupes.html"):
    '''
    View duplicates of this submission.
    '''
    context = {}
    extuser = request.extuser
    submit = get_object_or_404(Submission, id=submission_id)
    slogs = Submission.objects.filter(checksum=submit.checksum).order_by('-submit_time')
    
    context['submissions'] = paginate(request, slogs)
    return render_to_response(request, template_name, context)

@extuser_required()
def show_submits(request, template_name="receiver/show_submits.html"):
    '''
    View submissions for this domain.
    '''
    context = {}
    extuser = request.extuser
    slogs = Submission.objects.filter(domain=extuser.domain).order_by('-submit_time')
    
    context['submissions'] = paginate(request, slogs)
    return render_to_response(request, template_name, context)

@extuser_required()    
def single_attachment(request, attachment_id):
    try:
        attachment = Attachment.objects.get(id=attachment_id)
        mtype = mimetypes.guess_type(attachment.filepath)[0]
        if mtype == None:
            response = HttpResponse(mimetype='text/plain')
        else:
            response = HttpResponse(mimetype=mtype)
        fin = open(attachment.filepath ,'r')
        txt = fin.read()
        fin.close()
        response.write(txt) 
        return response
    except:
        return ""

@extuser_required()
def single_submission(request, submission_id, template_name="receiver/single_submission.html"):
    context = {}        
    slog = Submission.objects.all().filter(id=submission_id)
    context['submission_item'] = slog[0]
    rawstring = str(slog[0].raw_header)
    rawstring = rawstring.replace(': <',': "<')
    rawstring = rawstring.replace('>,','>",')
    rawstring = rawstring.replace('>}','>"}')
    processed_header = eval(rawstring)
    
    get_original = False
    for item in request.GET.items():
        if item[0] == 'get_original':
            get_original = True           
    
    if get_original:
        response = HttpResponse(mimetype='text/plain')
        fin = open(slog[0].raw_post ,'r')
        txt = fin.read()
        fin.close()
        response.write(txt) 
        return response
    
    attachments = Attachment.objects.all().filter(submission=slog[0])
    context ['processed_header'] = processed_header
    context['attachments'] = attachments
    return render_to_response(request, template_name, context)

def raw_submit(request, template_name="receiver/submit.html"):
    context = {}            
    # since this is not a real domain the following call will always
    # fail to the end-user, but at least we'll have saved the post
    # data and can have a record of the event.
    return _do_domain_submission(request, "NO_DOMAIN_SPECIFIED", template_name, is_resubmission=False)

def domain_resubmit(request, domain_name, template_name="receiver/submit.html"):
    return _do_domain_submission(request, domain_name, template_name, True)

def domain_submit(request, domain_name, template_name="receiver/submit.html"):
    return _do_domain_submission(request, domain_name, template_name, False)

def _do_domain_submission(request, domain_name, template_name="receiver/submit.html", is_resubmission=False):
    
    if request.method != 'POST':
        return HttpResponse("You have to POST to submit data.")

    # first save the file to disk so we have it around before doing anything else.
    try:
        submit_record = submitprocessor.save_post(request.META, request.raw_post_data)
    except Exception, e:
        return HttpResponseServerError("Saving submission failed!  This information probably won't help you: %s", e)
    
    # alright the save worked.  now do some post processing if we can 
    if domain_name[-1] == '/':
        # get rid of the trailing slash if it's there
        domain_name = domain_name[0:-1]
    
    logging.debug("begin domained raw_submit(): " + domain_name)
    try: 
        currdomain = Domain.objects.get(name=domain_name)
    except Domain.DoesNotExist:
        logging.error("Submission failed! %s isn't a known domain.  The file has been saved as %s" %
                       (domain_name, submit_record))
        response = SubmitResponse(status_code=404, or_status_code=4040, 
                                  or_status="%s isn't a known domain." % domain_name)
        return response.to_response()
    try: 
        new_submission = submitprocessor.do_submission_processing(request.META, submit_record, 
                                                                  currdomain, is_resubmission=is_resubmission)
        
        if request.extuser:
            new_submission.authenticated_to = request.extuser
            new_submission.save()
        
        # the receiver creates its own set of params it cares about 
        receiver_params = {}
        receiver_params['TransactionId'] = new_submission.transaction_uuid
        receiver_params['Submission'] = new_submission
        receiver_params['NumAttachments'] = len(new_submission.attachments.all())
        ways_handled = new_submission.ways_handled.all()
        # loop through the potential ways it was handled and see if any
        # of the apps want to override the response.  
        # TODO: the first response will override all the others.  These
        # need a priority and/or more engineering if we want to allow
        # multiple responses.  See reciever/__init__.py for an example
        # of this in action
        # NOTE
        for way_handled in ways_handled:
            app_name = way_handled.handled.app
            method_name = way_handled.handled.method
            try:
                module = __import__(app_name,fromlist=[''])
                if hasattr(module, method_name):
                    method = getattr(module, method_name)
                    response = method(way_handled, receiver_params)
                    if response and isinstance(response, HttpResponse):
                        return response
            except ImportError:
                # this is ok it just wasn't a valid handling method
                continue
        # either no one handled it, or they didn't want to override the 
        # response.  This falls back to the old default. 
        response = SubmitResponse(status_code=200, or_status_code=2000,
                                  submit_id=new_submission.id,
                                  **receiver_params)
        return response.to_response()
            
    except Exception, e:
        type, value, tb = sys.exc_info()
        traceback_string = "\n\nTRACEBACK: " + '\n'.join(traceback.format_tb(tb))
        logging.error("Submission error for domain %s, user: %s, data: %s" % \
                      (domain_name,str(request.user),str(request.raw_post_data)), \
                      extra={'submit_exception':str(e), 'submit_traceback':traceback_string, \
                             'submit_record':str(submit_record)})
        # should we return success or failure here?  I think failure, even though
        # we did save the xml successfully.
        response = SubmitResponse(status_code=500, or_status_code=5000, 
                                  or_status="FAIL. %s" % e)
        return response.to_response()

def backup(request, domain_name, template_name="receiver/backup.html"):
    context = {}    
    if request.method == 'POST':
        currdomain = Domain.objects.filter(name=domain_name)
        if len(currdomain) != 1:
            new_submission = '[error]'
        else:
            new_submission = submitprocessor.do_old_submission(request.META,request.raw_post_data, domain=currdomain[0])
                    
        if new_submission == '[error]':
            template_name="receiver/submit_failed.html"     
        else:
            #todo: get password presumably from the HTTP header            
            new_backup = Backup(submission=new_submission, password='password')
            new_backup.save()
            response = HttpResponse(mimetype='text/plain')          
                                      
            context['backup_id'] = new_backup.backup_code                        
            template_name="receiver/backup_complete.html"            
            from django.template.loader import render_to_string
            rendering = render_to_string('receiver/backup_complete.html', { 'backup_id': new_backup.backup_code })
            
            response.write(rendering)
            response['Content-length'] = len(rendering)
            return response                                         
            
    return render_to_response(request, template_name, context,mimetype='text/plain')


def restore(request, code_id, template_name="receiver/restore.html"):
    context = {}            
    logging.debug("begin restore()")
    # need to somehow validate password, presmuably via the header objects.
    restore = Backup.objects.all().filter(backup_code=code_id)
    if len(restore) != 1:
        template_name="receiver/nobackup.html"
        return render_to_response(request, template_name, context,mimetype='text/plain')
    original_submission = restore[0].submission
    attaches = Attachment.objects.all().filter(submission=original_submission)
    for attach in attaches:
        if attach.attachment_content_type == "text/xml":
            response = HttpResponse(mimetype='text/xml')
            fin = open(attach.filepath,'r')
            txt = fin.read()
            fin.close()
            response.write(txt)
            
            verify_checksum = hashlib.md5(txt).hexdigest()
            if verify_checksum == attach.checksum:                
                return response
            else:               
                continue
    
    template_name="receiver/nobackup.html"
    return render_to_response(request, template_name, context,mimetype='text/plain')
        
                           
                      
def save_post(request):
    '''Saves the body of a post in a file.  Doesn't do any processing
       of any kind.'''
    if request.method != 'POST':
        return HttpResponse("You have to POST to submit data.")
    try:
        submit_record = submitprocessor.save_post(request.META, request.raw_post_data)
        return HttpResponse("Thanks for submitting!  Pick up your file at %s" % newfilename)
    except Exception, e:
        return HttpResponseServerError("Submission failed!  This information probably won't help you: %s" % e)
    
@extuser_required()
def orphaned_data(request, template_name="receiver/show_orphans.html"):
    '''
     View data that we could not link to any known schema
    '''
    context = {}
    extuser = request.extuser
    if request.method == "POST":
        xformmanager = XFormManager()
        count = 0
        
        def _process(submission, action):
            if action == 'delete':
                submission.delete()
                return True
            elif action == 'resubmit':
                status = False
                try:
                    status = xformmanager.save_form_data(submission.xform.filepath, submission.xform)
                except StorageUtility.XFormError, e:
                    # if xform doesn't match schema, that's ok
                    pass
                return status
            return False            
        if 'select_all' in request.POST:
            submissions = Submission.objects.filter(domain=extuser.domain).order_by('-submit_time')
            # TODO - optimize this into 1 db call
            for submission in submissions:
                if submission.is_orphaned():
                    if _process(submission, request.POST['action']): 
                        count = count + 1
        else: 
            for i in request.POST.getlist('instance'):
                if 'checked_'+ i in request.POST:
                    submit_id = int(i)
                    submission = Submission.objects.get(id=submit_id)
                    if _process(submission, request.POST['action']): 
                        count = count + 1
        context['status'] = "%s attempted. %s forms processed." % \
                            (request.POST['action'], count)
    inner_qs = SubmissionHandlingOccurrence.objects.all().values('submission_id').query
    orphans = Submission.objects.filter(domain=extuser.domain).exclude(id__in=inner_qs)
    # We could also put a check in here to not display duplicate data
    # using 'if not orphan.is_duplicate()'
    context['submissions'] = paginate(request, orphans )
    return render_to_response(request, template_name, context)

@extuser_required()
@transaction.commit_on_success
def delete_submission(request, submission_id=None, template='receiver/confirm_delete.html'):
    context = {}
    extuser = request.extuser
    submission = get_object_or_404(Submission, pk=submission_id)
    if request.method == "POST":
        if request.POST["confirm_delete"]: # user has confirmed deletion.
            submission.delete()
            logging.debug("Submission %s deleted ", submission_id)
            return HttpResponseRedirect(reverse('show_submits'))
    context['object'] = submission
    context['type'] = 'Submission'
    return render_to_response(request, template, context)

@extuser_required()
def orphaned_data_xml(request):
    """
    Get a zip file containing all orphaned submissions
    """
    context = {}
    extuser = request.extuser
    inner_qs = SubmissionHandlingOccurrence.objects.all().values('pk').query
    orphans = Submission.objects.exclude(id__in=inner_qs)
    attachments = Attachment.objects.filter(submission__in=orphans)
    xforms = attachments.filter(attachment_uri=XFORM_URI)
    return get_zipfile( xforms.values_list('filepath', flat=True) )
