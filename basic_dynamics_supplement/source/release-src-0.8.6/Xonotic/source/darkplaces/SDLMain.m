                                                            
                                                              
                                                             

                                                       
  

#include <SDL.h>

#if SDL_MAJOR_VERSION == 1

#include "SDLMain.h"
#include <sys/param.h>                     
#include <unistd.h>

                                                                       
                                                                       
                      
@interface NSApplication(SDL_Missing_Methods)
- (void)setAppleMenu:(NSMenu *)menu;
@end

                                                                  
#define		SDL_USE_NIB_FILE	0

                                                                    
#define		SDL_USE_CPS		1
#ifdef SDL_USE_CPS
                       
typedef struct CPSProcessSerNum
{
	UInt32		lo;
	UInt32		hi;
} CPSProcessSerNum;

extern OSErr	CPSGetCurrentProcess( CPSProcessSerNum *psn);
extern OSErr 	CPSEnableForegroundOperation( CPSProcessSerNum *psn, UInt32 _arg2, UInt32 _arg3, UInt32 _arg4, UInt32 _arg5);
extern OSErr	CPSSetFrontProcess( CPSProcessSerNum *psn);

#endif                  

static int    gArgc;
static char  **gArgv;
static BOOL   gFinderLaunch;
static BOOL   gCalledAppMainline = FALSE;

static NSString *getApplicationName(void)
{
    const NSDictionary *dict;
    NSString *appName = 0;

                                        
    dict = (const NSDictionary *)CFBundleGetInfoDictionary(CFBundleGetMainBundle());
    if (dict)
        appName = [dict objectForKey: @"CFBundleName"];
    
    if (![appName length])
        appName = [[NSProcessInfo processInfo] processName];

    return appName;
}

#if SDL_USE_NIB_FILE
                                    
@interface NSString (ReplaceSubString)
- (NSString *)stringByReplacingRange:(NSRange)aRange with:(NSString *)aString;
@end
#endif

@interface NSApplication (SDLApplication)
@end

@implementation NSApplication (SDLApplication)
                                     
- (void)terminate:(id)sender
{
                               
    SDL_Event event;
    event.type = SDL_QUIT;
    SDL_PushEvent(&event);
}
@end

                                                                   
@implementation SDLMain

                                                              
- (void) setupWorkingDirectory:(BOOL)shouldChdir
{
    if (shouldChdir)
    {
        char parentdir[MAXPATHLEN];
        CFURLRef url = CFBundleCopyBundleURL(CFBundleGetMainBundle());
        CFURLRef url2 = CFURLCreateCopyDeletingLastPathComponent(0, url);
        if (CFURLGetFileSystemRepresentation(url2, 1, (UInt8 *)parentdir, MAXPATHLEN)) {
            chdir(parentdir);                                         
        }
        CFRelease(url);
        CFRelease(url2);
    }
}

#if SDL_USE_NIB_FILE

                                                                
- (void)fixMenu:(NSMenu *)aMenu withAppName:(NSString *)appName
{
    NSRange aRange;
    NSEnumerator *enumerator;
    NSMenuItem *menuItem;

    aRange = [[aMenu title] rangeOfString:@"SDL App"];
    if (aRange.length != 0)
        [aMenu setTitle: [[aMenu title] stringByReplacingRange:aRange with:appName]];

    enumerator = [[aMenu itemArray] objectEnumerator];
    while ((menuItem = [enumerator nextObject]))
    {
        aRange = [[menuItem title] rangeOfString:@"SDL App"];
        if (aRange.length != 0)
            [menuItem setTitle: [[menuItem title] stringByReplacingRange:aRange with:appName]];
        if ([menuItem hasSubmenu])
            [self fixMenu:[menuItem submenu] withAppName:appName];
    }
}

#else

static void setApplicationMenu(void)
{
                                        
    NSMenu *appleMenu;
    NSMenuItem *menuItem;
    NSString *title;
    NSString *appName;
    
    appName = getApplicationName();
    appleMenu = [[NSMenu alloc] initWithTitle:@""];
    
                        
    title = [@"About " stringByAppendingString:appName];
    [appleMenu addItemWithTitle:title action:@selector(orderFrontStandardAboutPanel:) keyEquivalent:@""];

    [appleMenu addItem:[NSMenuItem separatorItem]];

    title = [@"Hide " stringByAppendingString:appName];
    [appleMenu addItemWithTitle:title action:@selector(hide:) keyEquivalent:@"h"];

    menuItem = (NSMenuItem *)[appleMenu addItemWithTitle:@"Hide Others" action:@selector(hideOtherApplications:) keyEquivalent:@"h"];
    [menuItem setKeyEquivalentModifierMask:(NSAlternateKeyMask|NSCommandKeyMask)];

    [appleMenu addItemWithTitle:@"Show All" action:@selector(unhideAllApplications:) keyEquivalent:@""];

    [appleMenu addItem:[NSMenuItem separatorItem]];

    title = [@"Quit " stringByAppendingString:appName];
    [appleMenu addItemWithTitle:title action:@selector(terminate:) keyEquivalent:@"q"];

    
                                   
    menuItem = [[NSMenuItem alloc] initWithTitle:@"" action:nil keyEquivalent:@""];
    [menuItem setSubmenu:appleMenu];
    [[NSApp mainMenu] addItem:menuItem];

                                                                           
    [NSApp setAppleMenu:appleMenu];

                                                       
    [appleMenu release];
    [menuItem release];
}

                          
static void setupWindowMenu(void)
{
    NSMenu      *windowMenu;
    NSMenuItem  *windowMenuItem;
    NSMenuItem  *menuItem;

    windowMenu = [[NSMenu alloc] initWithTitle:@"Window"];
    
                         
    menuItem = [[NSMenuItem alloc] initWithTitle:@"Minimize" action:@selector(performMiniaturize:) keyEquivalent:@"m"];
    [windowMenu addItem:menuItem];
    [menuItem release];
    
                                   
    windowMenuItem = [[NSMenuItem alloc] initWithTitle:@"Window" action:nil keyEquivalent:@""];
    [windowMenuItem setSubmenu:windowMenu];
    [[NSApp mainMenu] addItem:windowMenuItem];
    
                                                                      
    [NSApp setWindowsMenu:windowMenu];

                                                       
    [windowMenu release];
    [windowMenuItem release];
}

                                       
static void CustomApplicationMain (int argc, char **argv)
{
    NSAutoreleasePool	*pool = [[NSAutoreleasePool alloc] init];
    SDLMain				*sdlMain;

                                                      
    [NSApplication sharedApplication];
    
#ifdef SDL_USE_CPS
    {
        CPSProcessSerNum PSN;
                                    
        if (!CPSGetCurrentProcess(&PSN))
            if (!CPSEnableForegroundOperation(&PSN,0x03,0x3C,0x2C,0x1103))
                if (!CPSSetFrontProcess(&PSN))
                    [NSApplication sharedApplication];
    }
#endif                  

                            
    [NSApp setMainMenu:[[NSMenu alloc] init]];
    setApplicationMenu();
    setupWindowMenu();

                                                     
    sdlMain = [[SDLMain alloc] init];
    [NSApp setDelegate:sdlMain];
    
                                   
    [NSApp run];
    
    [sdlMain release];
    [pool release];
}

#endif


  
                                                                        
                                                                      
                                                         
                                                                         
               
  
                                                                          
                                                                        
               
  
                                                                              
  
                                                                   
   
- (BOOL)application:(NSApplication *)theApplication openFile:(NSString *)filename
{
    const char *temparg;
    size_t arglen;
    char *arg;
    char **newargv;

    if (!gFinderLaunch)                                           
        return FALSE;

    if (gCalledAppMainline)                                              
        return FALSE;

    temparg = [filename UTF8String];
    arglen = SDL_strlen(temparg) + 1;
    arg = (char *) SDL_malloc(arglen);
    if (arg == NULL)
        return FALSE;

    newargv = (char **) realloc(gArgv, sizeof (char *) * (gArgc + 2));
    if (newargv == NULL)
    {
        SDL_free(arg);
        return FALSE;
    }
    gArgv = newargv;

    SDL_strlcpy(arg, temparg, arglen);
    gArgv[gArgc++] = arg;
    gArgv[gArgc] = NULL;
    return TRUE;
}


                                                                  
- (void) applicationDidFinishLaunching: (NSNotification *) note
{
    int status;

                                                                  
    [self setupWorkingDirectory:gFinderLaunch];

#if SDL_USE_NIB_FILE
                                                                             
    [self fixMenu:[NSApp mainMenu] withAppName:getApplicationName()];
#endif

                                           
    gCalledAppMainline = TRUE;
    status = SDL_main (gArgc, gArgv);

                                           
    exit(status);
}
@end


@implementation NSString (ReplaceSubString)

- (NSString *)stringByReplacingRange:(NSRange)aRange with:(NSString *)aString
{
    unsigned int bufferSize;
    unsigned int selfLen = [self length];
    unsigned int aStringLen = [aString length];
    unichar *buffer;
    NSRange localRange;
    NSString *result;

    bufferSize = selfLen + aStringLen - aRange.length;
    buffer = (unichar *)NSAllocateMemoryPages(bufferSize*sizeof(unichar));
    
                                    
    localRange.location = 0;
    localRange.length = aRange.location;
    [self getCharacters:buffer range:localRange];
    
                                     
    localRange.location = 0;
    localRange.length = aStringLen;
    [aString getCharacters:(buffer+aRange.location) range:localRange];
     
                                   
    localRange.location = aRange.location + aRange.length;
    localRange.length = selfLen - localRange.location;
    [self getCharacters:(buffer+aRange.location+aStringLen) range:localRange];
    
                             
    result = [NSString stringWithCharacters:buffer length:bufferSize];
    
    NSDeallocateMemoryPages(buffer, bufferSize);
    
    return result;
}

@end



#ifdef main
#  undef main
#endif


                                                                
int main (int argc, char **argv)
{
                                                   
                                                              
    if ( argc >= 2 && strncmp (argv[1], "-psn", 4) == 0 ) {
        gArgv = (char **) SDL_malloc(sizeof (char *) * 2);
        gArgv[0] = argv[0];
        gArgv[1] = NULL;
        gArgc = 1;
        gFinderLaunch = YES;
    } else {
        int i;
        gArgc = argc;
        gArgv = (char **) SDL_malloc(sizeof (char *) * (argc+1));
        for (i = 0; i <= argc; i++)
            gArgv[i] = argv[i];
        gFinderLaunch = NO;
    }

#if SDL_USE_NIB_FILE
    NSApplicationMain (argc, argv);
#else
    CustomApplicationMain (argc, argv);
#endif
    return 0;
}

#endif
